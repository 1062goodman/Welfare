import os
from dotenv import load_dotenv, find_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_upstage import ChatUpstage
from langchain_upstage.embeddings import UpstageEmbeddings

from state import  SimpleExtraction, AgentState
from prompts import (
    ANSWER_SYSTEM_PROMPT
)

# ---------------------------------------------------------
# LLM 
load_dotenv(find_dotenv())
api_key=os.getenv('UPSTAGE_API_KEY')

#대화
chat_llm = ChatUpstage(model="solar-pro")

#임베딩 모델
query_emb_model = UpstageEmbeddings(
    api_key=api_key,
    model="solar-embedding-1-large-query"
)
#db연결
graph = Neo4jGraph()


# --------------------------------------------------------- 
# llm 체인
extraction_llm = chat_llm.with_structured_output(SimpleExtraction)

EXTRACTION_PROMPT = """사용자의 질문에서 복지 정책 검색에 필요한 정보를 추출하세요.
의도를 분류하거나 되묻지 말고, 질문에서 파악 가능한 정보만 그대로 추출하세요."""

extraction_chain = ChatPromptTemplate.from_messages([
    ("system", EXTRACTION_PROMPT),
    ("placeholder", "{messages}")
]) | extraction_llm

def graphrag_search_node(state: AgentState):
    print("[순수 GraphRAG] 추출 + 검색")
    messages = state["messages"]
    query = messages[-1].content

    # 1회 추출 (라우팅/재질문 없음)
    result = extraction_chain.invoke({"messages": messages})

    # 기존 execute_search_node와 동일한 그래프 필터+검색 로직
    graph_filters = ""
    if result.life_cycle:
        graph_filters += "MATCH (p)-[:TARGETS_AGE]->(l:LifeCycle) WHERE l.name IN $life_cycle\n"
    if result.target_group:
        graph_filters += "MATCH (p)-[:TARGETS_GROUP]->(t:TargetGroup) WHERE t.name IN $target_group\n"
    if result.theme:
        graph_filters += "MATCH (p)-[:RELATES_TO]->(th:Theme) WHERE th.name IN $theme\n"

    params = {"life_cycle": result.life_cycle, "target_group": result.target_group, "theme": result.theme}
    records = []

    search_terms = list(set(result.policy_names + result.search_keywords))
    if search_terms:
        params["ft_query"] = " AND ".join(search_terms)
        cypher_ft = f"""
        CALL db.index.fulltext.queryNodes('policy_name_index', $ft_query) YIELD node AS p, score AS ft_score
        {graph_filters}
        OPTIONAL MATCH (p)-[:MANAGED_BY]->(d:Department)
        RETURN p.servNm AS title, p.servDgst AS digest, d.name AS department, ft_score AS score
        LIMIT 3
        """
        try:
            records = graph.query(cypher_ft, params=params)
        except Exception:
            records = []

    if not records:
        embedding = query_emb_model.embed_query(query)
        params["query_embedding"] = embedding
        cypher_vec = f"""
        CALL db.index.vector.queryNodes('chunk_embedding_index', 15, $query_embedding) YIELD node AS c, score AS vec_score
        MATCH (p:Policy)-[:HAS_INFO]->(c)
        {graph_filters}
        WITH p, max(vec_score) AS max_score
        WHERE max_score >= 0.63
        ORDER BY max_score DESC LIMIT 5
        OPTIONAL MATCH (p)-[:MANAGED_BY]->(d:Department)
        RETURN p.servNm AS title, p.servDgst AS digest, d.name AS department, max_score AS score
        """
        records = graph.query(cypher_vec, params=params)

    formatted = "\n\n".join(
        f"[{r['title']}] 담당부처: {r.get('department', '정보없음')}\n요약: {r['digest']}"
        for r in records
    ) or "조건에 맞는 복지 정책을 찾지 못했습니다."

    return {"search_results": formatted}



# --------------------------------------------
# 답변생성
def graphrag_answer_node(state: AgentState):
    print("[순수 GraphRAG] 답변 생성")
    search_results = state.get("search_results", "검색 결과가 없습니다.")
    guide = "검색된 정책들을 간단히 소개하세요."

    formatted_prompt = ANSWER_SYSTEM_PROMPT.format(guide=guide, search_results=search_results)
    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        MessagesPlaceholder(variable_name="messages")
    ])
    response = (prompt | chat_llm).invoke({"messages": state["messages"]})
    return {"messages": [response]}

# --------------------------------------------------------- 
# 공격방어

def block_attack_node(state: AgentState):
    print("프롬프트 공격 방어")

    response = "서비스 검색과 무관한 지시, 시스템 설정을 변경하려는 요청은 응답할수없습니다."
    return {"messages": [AIMessage(content=response)]}

# --------------------------------------------------------- 

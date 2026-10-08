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
chat_llm = ChatUpstage(model="solar-pro", timeout=60, max_retries=1, temperature=0)

#임베딩 모델
query_emb_model = UpstageEmbeddings(api_key=api_key, model="solar-embedding-1-large-query", timeout=60)
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
    result = None
    for _ in range(2):
        try:
            result = extraction_chain.invoke({"messages": messages})
        except Exception as e:
            print(f"추출 호출 실패: {e}")
        if result is not None:
            break
    if result is None:
        result = SimpleExtraction()

    life_cycle = ["임신 · 출산" if x == "임신·출산" else x for x in result.life_cycle]
    params = {"life_cycle": life_cycle, "target_group": result.target_group, "theme": result.theme}

    # 기존 execute_search_node와 동일한 그래프 필터+검색 로직
    graph_filters = ""
    if result.life_cycle:
        graph_filters += "MATCH (p)-[:TARGETS_AGE]->(l:LifeCycle) WHERE l.name IN $life_cycle\n"
    if result.target_group:
        graph_filters += "MATCH (p)-[:TARGETS_GROUP]->(t:TargetGroup) WHERE t.name IN $target_group\n"
    if result.theme:
        graph_filters += "MATCH (p)-[:RELATES_TO]->(th:Theme) WHERE th.name IN $theme\n"

    records = []

    search_terms = list(set(result.policy_names + result.search_keywords))
    if search_terms:
        names = [n.replace('"', '').strip() for n in search_terms if n.strip()]
        params["ft_query"] = " OR ".join(f'"{n}"' for n in names)
        cypher_ft = """
        CALL db.index.fulltext.queryNodes('policy_name_index', $ft_query) YIELD node AS p, score AS ft_score
        OPTIONAL MATCH (p)-[:MANAGED_BY]->(d:Department)
        RETURN p.servId AS id, p.servNm AS title, p.servDgst AS digest, d.name AS department,
               [(p)-[:PROVIDES]->(s:SupportType) | s.name][0] AS support_type, ft_score AS score,
               [(p)-[:HAS_INFO]->(c) | {type: c.type, content: c.content, score: 0.0}] AS hits
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
        CALL db.index.vector.queryNodes('chunk_embedding_index', 30, $query_embedding) YIELD node AS c, score AS vec_score
        MATCH (p:Policy)-[:HAS_INFO]->(c)
        {graph_filters}
        WITH p, max(vec_score) AS max_score, collect({{type: c.type, content: c.content, score: vec_score}}) AS hits
        WHERE max_score >= 0.63
        ORDER BY max_score DESC LIMIT 5
        OPTIONAL MATCH (p)-[:MANAGED_BY]->(d:Department)
        RETURN p.servId AS id, p.servNm AS title, p.servDgst AS digest, d.name AS department,
               [(p)-[:PROVIDES]->(s:SupportType) | s.name][0] AS support_type, max_score AS score, hits
        """
        records = graph.query(cypher_vec, params=params)

    texts = []
    for i, r in enumerate(records):
        seen, parts = set(), []
        for h in sorted(r["hits"], key=lambda h: h["score"], reverse=True):
            if h["type"] in seen:
                continue
            seen.add(h["type"])
            parts.append(f"■ {h['type']}\n{(h['content'] or '')[:1200]}")
            if len(parts) >= 2:
                break
        body = "\n\n".join(parts) or f"- 요약: {r['digest']}"
        texts.append(f"[{i+1}순위] 정책명: {r['title']} (Score: {r['score']:.4f})\n"
                     f"- 담당부처: {r.get('department') or '정보없음'}\n"
                     f"- 제공유형: {r.get('support_type') or '정보없음'}\n{body}\n{'-' * 30}")
    formatted = "\n".join(texts) or "조건에 맞는 복지 정책을 찾지 못했습니다."
    print(f"[경로] {'fulltext' if search_terms and records and not params.get('query_embedding') else 'vector'}, {len(records)}건")
    return {"search_results": formatted,
            "recommended_ids": [r["id"] for r in records],
            "recommended_names": [r["title"] for r in records]}



# --------------------------------------------
# 답변생성
def graphrag_answer_node(state: AgentState):
    print("[순수 GraphRAG] 답변 생성")
    search_results = state.get("search_results", "검색 결과가 없습니다.")
    if search_results.startswith("조건에 맞는 복지 정책을 찾지 못했습니다"):
            return {"messages": [AIMessage(content="조건에 맞는 정책을 찾지 못했습니다. 상황을 조금 다르게 말씀해 주시면 다시 찾아볼게요.")]}
    guide =  ("여러 정책의 [목록과 요약]을 제공 중입니다. 사용자가 신청 방법, 지원 대상, 지원 내용 등 특정 정보를 물었다면 "
             "그 정보를 먼저 답하세요. 요약하여 소개한 뒤 '더 자세히 알고 싶은 정책이 있다면 번호나 이름을 말씀해 주세요'라고 유도하세요.")

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

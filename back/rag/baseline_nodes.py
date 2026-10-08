from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from state import AgentState
from prompts import ANSWER_SYSTEM_PROMPT
from nodes import query_emb_model, graph, chat_llm  

def naive_rag_node(state: AgentState):
    print("[베이스라인] 벡터 검색만 수행")
    query = state["messages"][-1].content
    embedding = query_emb_model.embed_query(query)

    records = graph.query("""
        CALL db.index.vector.queryNodes('chunk_embedding_index', 5, $embedding)
        YIELD node AS c, score
        MATCH (p:Policy)-[:HAS_INFO]->(c)
        RETURN p.servId AS id, p.servNm AS title, c.type AS type, c.content AS content, score
    """, params={"embedding": embedding})

    formatted = "\n".join(
        f"[{i+1}순위] 정책명: {r['title']}\n■ {r['type']}\n{(r['content'] or '')[:1200]}\n{'-' * 30}"
        for i, r in enumerate(records)
    ) or "검색 결과가 없습니다."
    names = list(dict.fromkeys(r["title"] for r in records))
    return {"search_results": formatted, "recommended_names": names}


def naive_answer_node(state: AgentState):
    print("[베이스라인] 답변 생성")
    search_results = state.get("search_results", "검색 결과가 없습니다.")
    guide = "여러 정책의 [목록과 요약]을 제공 중입니다. 사용자가 신청 방법, " \
    "지원 대상, 지원 내용 등 특정 정보를 물었다면 그 정보를 먼저 답하세요. 요약하여 소개한 뒤 '더 자세히 알고 싶은 정책이 있다면 번호나 이름을 말씀해 주세요'라고 유도하세요."

    formatted_prompt = ANSWER_SYSTEM_PROMPT.format(guide=guide, search_results=search_results)
    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        MessagesPlaceholder(variable_name="messages")
    ])

    response = (prompt | chat_llm).invoke({"messages": state["messages"]})
    return {"messages": [response]}
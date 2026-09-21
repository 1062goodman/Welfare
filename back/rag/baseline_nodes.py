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
        RETURN p.servNm AS title, c.content AS digest, score
    """, params={"embedding": embedding})

    formatted = "\n\n".join(f"[{r['title']}] {r['digest']}" for r in records) or "검색 결과가 없습니다."
    return {"search_results": formatted}


def naive_answer_node(state: AgentState):
    print("[베이스라인] 답변 생성")
    search_results = state.get("search_results", "검색 결과가 없습니다.")
    guide = "검색된 정책들을 간단히 소개하세요."

    formatted_prompt = ANSWER_SYSTEM_PROMPT.format(guide=guide, search_results=search_results)
    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        MessagesPlaceholder(variable_name="messages")
    ])

    response = (prompt | chat_llm).invoke({"messages": state["messages"]})
    return {"messages": [response]}
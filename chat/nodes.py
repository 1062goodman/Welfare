import os
from dotenv import load_dotenv, find_dotenv
from langchain_upstage.embeddings import UpstageEmbeddings
from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_upstage import ChatUpstage


from state import AgentState, IntentClassification


from prompts import (
    INTENT_SYSTEM_PROMPT, 
    ANSWER_SYSTEM_PROMPT, 
    GENERAL_CHAT_PROMPT, 
    ASK_DETAILS_PROMPT
)

# ---------------------------------------------------------
# LLM 
load_dotenv(find_dotenv())
api_key=os.getenv('UPSTAGE_API_KEY')
#의도분류
llm = ChatUpstage(model="solar-pro")
structured_llm = llm.with_structured_output(IntentClassification)

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
# 의도 분류

# 의도 분류 시스템 프롬프트 

intent_prompt = ChatPromptTemplate.from_messages([
    ("system", INTENT_SYSTEM_PROMPT),
    ("placeholder", "{messages}") # 이전 대화 기록
])

# 프롬프트와 LLM 체인 연결
intent_chain = intent_prompt | structured_llm


def classify_intent_node(state: AgentState):

    messages = state["messages"]
    
    result = intent_chain.invoke({"messages": messages})
    
    print(f"분석 결과: {result.intent} (이유: {result.reasoning})")
    print(f"추출된 조건: {result.conditions}")
    print("\n\n")
    
    
    return {
        "intent": result.intent,
        "conditions": result.conditions,
        "target_policy": result.target_policy
    }






# --------------------------------------------
# 검색
def execute_search_node(state: AgentState):
    print("db 검색")
    
    # 마지막 쿼리 추출
    latest_message = state["messages"][-1].content
    conditions = state.get("conditions", {})
    
    # 검색어 보강 
    search_query = f"질문: {latest_message}\n조건: {conditions}"
    
    # 4096차원 벡터 변환
    query_embedding = query_emb_model.embed_query(search_query)
    

    cypher_query = """
    CALL db.index.vector.queryNodes('chunk_embedding_index', 10, $query_embedding)
    YIELD node AS c, score
    MATCH (p:Policy)-[:HAS_INFO]->(c)
    WITH p, max(score) AS max_score
    WHERE max_score >= $threshold
    ORDER BY max_score DESC 
    OPTIONAL MATCH (p)-[:MANAGED_BY]->(d:Department)
    OPTIONAL MATCH (p)-[:PROVIDES]->(s:SupportType)
    RETURN p.servId AS id, 
           p.servNm AS title, 
           p.servDgst AS digest, 
           d.name AS department,
           s.name AS support_type,
           max_score AS score 
    """
    
    similarity_threshold = 0.63
    records = graph.query(cypher_query, params={"query_embedding": query_embedding,
                                                "threshold": similarity_threshold})
    
    # 텍스트 가공
    if not records:
        formatted_results = "조건에 맞는 복지 정책을 찾지 못했습니다."
    else:
        result_texts = []
        rec_ids = []
        rec_names = []
        for i, record in enumerate(records):
            # score(유사도)가 반환되므로, 내부 디버깅이나 컷오프(Cut-off) 기준으로 활용할 수 있습니다.
            rec_ids.append(record['id'])
            rec_names.append(record['title'])
            text = (
                f"설정한 임계 점수: {similarity_threshold}\n"
                f"[{i+1}순위] 정책명: {record['title']} )\n"
                f"- 담당부처: {record.get('department', '정보없음')}\n"
                f"- 제공유형: {record.get('support_type', '정보없음')}\n"
                f"- 요약: {record['digest']}\n"
                f"-" * 30
            )
            result_texts.append(text)
        
        formatted_results = "\n".join(result_texts)
        
    print(f"{len(records)}개 검색 완료")
    print(f"{rec_ids}")
    print(f"{rec_names}")
    
    for i, rec in enumerate(records):
        print(f"[{i+1}] {rec['title']} - Score: {rec['score']:.4f}")
    
 
    return {
        "search_results": "\n".join(result_texts),
        "recommended_ids": rec_ids,       # 리스트 형태 보존
        "recommended_names": rec_names    # 리스트 형태 보존
    }


# --------------------------------------------
# 상세 검색
def execute_detail_search_node(state: AgentState):
    print("상세 정보 가져오기")
    
    target = state.get("target_policy", "")
    rec_ids = state.get("recommended_ids", [])
    
    # 예외처리: 추천해 둔 ID가 없을 때
    if not rec_ids:
        return {"search_results": "이전에 추천해 드린 정책 목록이 없어 상세 정보를 가져올 수 없습니다. 다시 검색해 주세요."}
    
    # 사용자의 발화에서 번호 유추 (1번, 2번, 3번)
    target_id = rec_ids[0] # 기본값 (알 수 없으면 1번)
    if "1" in target or "첫" in target: target_id = rec_ids[0]
    elif "2" in target or "두" in target and len(rec_ids) > 1: target_id = rec_ids[1]
    elif "3" in target or "세" in target and len(rec_ids) > 2: target_id = rec_ids[2]
    
    cypher_query = """
    MATCH (p:Policy {servId: $target_id})-[:HAS_INFO]->(c:Chunk)
    RETURN p.servNm AS title, c.type AS type, c.content AS content
    """
    
    records = graph.query(cypher_query, params={"target_id": target_id})
    
    if not records:
        return {"search_results": "해당 정책의 상세 정보를 찾을 수 없습니다."}
    
    # 상세 정보 텍스트 가공
    title = records[0]['title']
    detail_text = f"[{title}] 상세 정보입니다.\n\n"
    for record in records:
        detail_text += f"■ {record['type']}\n{record['content']}\n\n"
        
  
    return {"search_results": detail_text}


from langchain_core.messages import AIMessage


# --------------------------------------------
# 답변생성
def generate_answer_node(state: AgentState):
    print("답변 생성")
    
    messages = state["messages"] 
    search_results = state.get("search_results", "검색 결과가 없습니다.")

    intent = state.get("intent", "")
    
    if intent == "상세요구":
        guide = "사용자가 선택한 정책의 [상세 정보]를 제공 중입니다. 정보를 누락하지 말고 상세하고 친절하게 정리해 주세요."
    else:
        guide = "여러 정책의 [목록과 요약]을 제공 중입니다. 요약하여 소개한 뒤 '더 자세히 알고 싶은 정책이 있다면 번호나 이름을 말씀해 주세요'라고 유도하세요."


    formatted_prompt = ANSWER_SYSTEM_PROMPT.format(
        guide=guide, 
        search_results=search_results
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        MessagesPlaceholder(variable_name="messages") 
    ])
   
    
    
    chain = prompt | chat_llm
    response = chain.invoke({
        "guide":guide,
        "search_results": search_results,
        "messages": messages
    })
    
    return {"messages": [response]}

# --------------------------------------------------------- 
# 일상 대화

def general_chat_node(state: AgentState):
    print("일상 대화 답변 생성")
    
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", GENERAL_CHAT_PROMPT),
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
# 슬롯필링

def ask_for_details_node(state: AgentState):
    print("부족한 조건 묻기")
    
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", ASK_DETAILS_PROMPT),
        MessagesPlaceholder(variable_name="messages")
    ])
    
    response = (prompt | chat_llm).invoke({"messages": state["messages"]})
    return {"messages": [response]}
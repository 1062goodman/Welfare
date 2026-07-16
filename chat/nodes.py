import os
from dotenv import load_dotenv, find_dotenv
from langchain_upstage.embeddings import UpstageEmbeddings
from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_upstage import ChatUpstage


from state import AgentState, IntentClassification

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
intent_system_prompt = """당신은 대한민국 복지 정책 안내 챗봇의 분석가입니다.
사용자의 입력(대화 기록 포함)을 분석하여 의도를 파악하고, 검색 조건을 추출하세요.

[의도 분류 기준]
1. 일상대화: 인사, 챗봇의 신원 확인, 복지와 무관한 질문 (예: "안녕?", "넌 누구니?"). 
2. 조건부족: 복지 정책을 묻고 있으나, 대상자를 특정할 수 있는 정보(나이, 직업, 가구 상황 등)가 전혀 없는 경우 (예: "받을 수 있는 지원금 있어?")
3. 검색가능: 복지 정책을 묻고 있으며, 사용자 상황을 유추할 수 있는 조건이 '최소 1개 이상' 포함된 경우 (예: "나 20대인데 취업지원금 찾아줘", "퇴사했는데 돈 받을 수 있을까?")
4. 상세요구: 챗봇이 이전에 추천해준 정책 목록 중 특정 정책에 대해 상세 정보, 신청 방법, 지원 금액 등을 요구하는 경우 (예: "1번 자세히 알려줘", "두 번째 거 신청방법은?", "청년도약계좌 조건 알려줘")

[조건 추출 방법 (의도가 '검색가능'인 경우에만)]
사용자의 발화에서 다음 요소들이 있다면 JSON(딕셔너리) 형태로 추출하세요.
- 생애주기: 청년, 중장년, 노년, 임신/출산 등
- 상황키워드: 퇴사, 구직중, 출산, 저소득 등 문장에 포함된 구체적 상황
"""

intent_prompt = ChatPromptTemplate.from_messages([
    ("system", intent_system_prompt),
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
    ORDER BY max_score DESC LIMIT 3
    OPTIONAL MATCH (p)-[:MANAGED_BY]->(d:Department)
    OPTIONAL MATCH (p)-[:PROVIDES]->(s:SupportType)
    RETURN p.servId AS id, 
           p.servNm AS title, 
           p.servDgst AS digest, 
           d.name AS department,
           s.name AS support_type,
           max_score AS score 
    """
    
    
    records = graph.query(cypher_query, params={"query_embedding": query_embedding})
    
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
        guide = "사용자가 선택한 정책의 [상세 정보]를 제공 중입니다. 정보를 누락하거나, 당신의 이전 지식을 임의로 채우지 말고 정리해 주세요."
    else:
        guide = "여러 정책의 [목록과 요약]을 제공 중입니다. 요약하여 소개한 뒤, 대화 마지막에 '더 자세히 알고 싶은 정책이 있다면 번호나 이름을 말씀해 주세요'라고 유도하세요."

    system_prompt = """당신은 대한민국 복지 정책을 안내하는 친절하고 전문적인 상담원입니다.
아래 제공된 반드시 아래에 제공된 [검색 데이터]를 바탕으로 사용자의 질문에 답변하세요.


[절대 규칙]
1. 오직 제공된 [검색 데이터]에 있는 정보만 사용하세요. 
2. 만약 [검색 데이터]에 '필요 서류'나 '임대 조건'에 대한 정보가 없다면, "제공된 데이터에는 해당 상세 정보가 포함되어 있지 않습니다"라고 명확히 밝히세요.
3. 당신의 내부 사전 지식이나 일반적인 상식으로 내용을 보충하지 마세요.
4. 만약 [검색 데이터]에 있는 정보만을 설명하는데 그치지 않고 당신이 임의로 보충한 내용을 설명한다면 사용자는 위험에 빠지게 됩니다.

[답변 가이드라인]
1. 가장 중요한 것은 반드시 검색 데이터로만 답변하는것입니다. 만약 정책이 1개만 있다면 1개, 3개가 있다면 3개만 안내하세요. (사용자가 원하더라도 절대 당신이 알고있는 외부 지식을 임의로 추가하여 개수를 늘리면 안됩니다.)
2. {guide}
3. 사용자 상황에 공감하며 친절하게 답변을 시작하세요. 
4. 검색된 정책 중 사용자의 질문과 가장 적합한 것을 중심으로 설명하세요.
5. 정책명, 담당부처, 요약, 핵심 지원 대상을 보기 좋게 불릿 포인트(*)나 이모지를 활용해 정리하세요.
6. 검색 결과에 없는 내용은 절대 지어내지 마세요. (환각 방지 철저)

[검색 데이터]
{search_results}
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
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
    
    system_prompt = """당신은 대한민국 복지 정책 안내 챗봇입니다. 
사용자에게 친절하고 따뜻하게 인사하거나 일상적인 대화에 응답하세요. 
사용자는 도움이 필요한 상황일 가능성이 큽니다. "배고파"와 같은 대화에도 도움이 필요할수도 있으니 
대화 마무리에는 "어떤 복지 정책이 궁금하신가요?" 등 복지 안내를 돕겠다는 의지를 보여주세요."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages")
    ])
    
    response = (prompt | chat_llm).invoke({"messages": state["messages"]})
    return {"messages": [response]}

# --------------------------------------------------------- 
# 슬롯필링

def ask_for_details_node(state: AgentState):
    print("부족한 조건 묻기")
    
    system_prompt = """당신은 대한민국 복지 정책 안내 챗봇입니다.
사용자가 복지 혜택을 찾고 있으나, 정책을 검색하기 위한 정보(연령대, 소득 기준, 가구 상황, 취업 여부 등)가 부족합니다.
사용자의 이전 발화를 확인한 후, 더 정확한 맞춤형 검색을 위해 어떤 구체적인 정보가 필요한지 하나만 집어서 부드럽고 친절하게 질문하세요."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages")
    ])
    
    response = (prompt | chat_llm).invoke({"messages": state["messages"]})
    return {"messages": [response]}
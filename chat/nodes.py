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
    ASK_DETAILS_PROMPT,
    SUMMERIZE_SYSTEM_PROMPT
)

# ---------------------------------------------------------
# LLM 
load_dotenv(find_dotenv())
api_key=os.getenv('UPSTAGE_API_KEY')

#선요약
summarize_llm = ChatUpstage(model="solar-mini")

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

    policy_names = getattr(result, 'policy_names', [])
    life_cycle = getattr(result, 'life_cycle', [])
    target_group = getattr(result, 'target_group', [])
    theme = getattr(result, 'theme', [])

    filled_slots_count = sum(1 for slot in [life_cycle, target_group, theme] if len(slot) > 0)

    if len(policy_names) > 0 or filled_slots_count >= 2:
        final_intent = "검색가능"
    else:
        final_intent = "조건부족"

        
    print(f"분석 결과: {final_intent} (이유: {result.reasoning})")
    print(f"추출된 정책명: {result.policy_names}")
    print(f"추출된 조건: 생애({result.life_cycle}), 가구({result.target_group}), 주제({result.theme})")
    print("\n\n")
    
    
    return {
        "intent": final_intent,
        "policy_names": result.policy_names,
        "life_cycle": result.life_cycle,
        "target_group": result.target_group,
        "theme": result.theme,
        "target_policy": result.target_policy
    }

# --------------------------------------------
# 선요약

summarize_prompt = ChatPromptTemplate.from_messages([
    ("system", SUMMERIZE_SYSTEM_PROMPT),
    ("placeholder", "{messages}") # 이전 대화 기록
])

summarize_chain = summarize_prompt | summarize_llm

def pre_summarize_node(state: AgentState):

    messages = state["messages"]
    latest_user_message = messages[-1].content

    if len(latest_user_message) > 300:
        print("300자 초과하여 요약 실행")
        response = summarize_chain.invoke({"messages": [messages[-1]]})
        latest_user_message = response.content
        print(f"요약된 문장:\n{latest_user_message}")

    #"current_query" 필드에 가장 최근의 메시지를 넣음. (요약된것이든 원문이든)
    return {"current_query": latest_user_message}




# --------------------------------------------
# 검색
def execute_search_node(state: AgentState):
    print("db 검색")
    
    # 마지막 쿼리, 조건 추출
    latest_message = state["current_query"]
    policy_names = state.get("policy_names", [])
    life_cycle = state.get("life_cycle", [])
    target_group = state.get("target_group", [])
    theme = state.get("theme", [])

    #조건으로 필터링
    graph_filters = ""
    if life_cycle:
        graph_filters += "MATCH (p)-[:TARGETS_AGE]->(l:LifeCycle) WHERE l.name IN $life_cycle\n"
    if target_group:
        graph_filters += "MATCH (p)-[:TARGETS_GROUP]->(t:TargetGroup) WHERE t.name IN $target_group\n"
    if theme:
        graph_filters += "MATCH (p)-[:RELATES_TO]->(th:Theme) WHERE th.name IN $theme\n"

    params = {
        "life_cycle": life_cycle,
        "target_group": target_group,
        "theme": theme,
        "threshold": 0.63
    }

    records = []

    # 검색어 보강 
    if policy_names:
        print(f"Full-Text 검색 시도 ({policy_names})")
        # 배열을 OR 조건 문자열로 조립 (예: "장애인연금 OR 장애수당")
        ft_query_string = " OR ".join(policy_names)
        params["ft_query"] = ft_query_string
        
       
        cypher_ft = f"""
        CALL db.index.fulltext.queryNodes('policy_name_index', $ft_query) YIELD node AS p, score AS ft_score
        {graph_filters}
        OPTIONAL MATCH (p)-[:MANAGED_BY]->(d:Department)
        OPTIONAL MATCH (p)-[:PROVIDES]->(s:SupportType)
        RETURN p.servId AS id, p.servNm AS title, p.servDgst AS digest, 
               d.name AS department, s.name AS support_type, ft_score AS score
        LIMIT 3
        """
        records = graph.query(cypher_ft, params=params)

    if (not policy_names) or (not records):
        print("벡터 검색 시도")
        
        # 쿼리 확장: 벡터 검색의 정확도를 높이기 위해 확장된 키워드들을 모두 합쳐서 임베딩
        combined_query = f"{latest_message} " + " ".join(policy_names + life_cycle + target_group + theme)
        query_embedding = query_emb_model.embed_query(combined_query)
        params["query_embedding"] = query_embedding
        
        cypher_vec = f"""
        CALL db.index.vector.queryNodes('chunk_embedding_index', 15, $query_embedding) YIELD node AS c, score AS vec_score
        MATCH (p:Policy)-[:HAS_INFO]->(c)
        {graph_filters}
        WITH p, max(vec_score) AS max_score
        WHERE max_score >= $threshold
        ORDER BY max_score DESC
        LIMIT 5
        OPTIONAL MATCH (p)-[:MANAGED_BY]->(d:Department)
        OPTIONAL MATCH (p)-[:PROVIDES]->(s:SupportType)
        RETURN p.servId AS id, p.servNm AS title, p.servDgst AS digest, 
               d.name AS department, s.name AS support_type, max_score AS score
        """
        records = graph.query(cypher_vec, params=params)


    
    if not records:
        formatted_results = "조건에 맞는 복지 정책을 찾지 못했습니다."
        rec_ids, rec_names = [], []
    else:
        result_texts = []
        rec_ids, rec_names = [], []
        
        for i, record in enumerate(records):
            rec_ids.append(record['id'])
            rec_names.append(record['title'])
            text = (
                f"[{i+1}순위] 정책명: {record['title']} (Score: {record['score']:.4f})\n"
                f"- 담당부처: {record.get('department', '정보없음')}\n"
                f"- 제공유형: {record.get('support_type', '정보없음')}\n"
                f"- 요약: {record['digest']}\n")+ f"{'-' * 30}"
            
            result_texts.append(text)
            
        formatted_results = "\n".join(result_texts)
        
        print(f"{len(records)}개 정책 검색: {rec_names}")
    

   
    return {
        "search_results": formatted_results,
        "recommended_ids": rec_ids,       
        "recommended_names": rec_names    
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
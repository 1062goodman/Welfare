import os
from dotenv import load_dotenv, find_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_upstage import ChatUpstage
from langchain_upstage.embeddings import UpstageEmbeddings

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
    current_names = state.get("current_recommended_names", [])

    result = intent_chain.invoke({"messages": messages,
                                  "current_recommendations":current_names})

    policy_names = getattr(result, 'policy_names', [])
    search_keywords = getattr(result, 'search_keywords', [])
    life_cycle = getattr(result, 'life_cycle', [])
    target_group = getattr(result, 'target_group', [])
    theme = getattr(result, 'theme', [])

    filled_slots_count = sum(1 for slot in [life_cycle, target_group, theme] if len(slot) > 0)

    if len(policy_names) > 0 or filled_slots_count >= 2:
        final_intent = "검색가능"
    else:
        final_intent = "조건부족"

        
    print(f"분석 결과: {final_intent} (이유: {result.reasoning})")
    print(f"추출된 정책명: {policy_names}")
    print(f"추출된 키워드: {search_keywords}")
    print(f"추출된 조건: 생애({life_cycle}), 가구({target_group}), 주제({theme})")
    print("\n\n")
    
    
    return {
        "intent": final_intent,
        "search_keywords": search_keywords,
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
    search_keywords = state.get("search_keywords", [])
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

    # full-text 검색
    search_terms = list(set(policy_names + search_keywords))
    if search_terms:
        print(f"Full-Text 검색 시도 ({search_terms})")
        ft_query_string = " AND ".join(search_terms) # 키워드들을 모두 포함하는 엄격한 검색
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
        try:
            records = graph.query(cypher_ft, params=params)
            print(f"full-context 검색 결과: {records}")
        except Exception as e:
            print(f"Full-Text 검색 중 예외 발생 (무시하고 벡터로 전환): {e}")
            records = []
        
        

    if not records:
        print("벡터 검색 시도")
        combined_query = f"{latest_message} " + " ".join(search_terms + life_cycle + target_group + theme)
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
        "recommended_names": rec_names,
        "current_recommended_ids": rec_ids,
        "current_recommended_names": rec_names 
    }


# --------------------------------------------
# 상세 검색
def execute_detail_search_node(state: AgentState):
    print("상세 정보 가져오기")
    
    targets = state.get("target_policy", [])
    curr_ids = state.get("current_recommended_ids", [])
    all_ids = state.get("recommended_ids", [])
    all_names = state.get("recommended_names", [])
    
    # 예외처리: 추천해 둔 ID가 없을 때
    if not all_ids:
        return {"search_results": "이전에 추천해 드린 정책 목록이 없어 상세 정보를 가져올 수 없습니다. 다시 검색해 주세요."}
    
    matched_ids = []

    for target in targets:
        # 순수 숫자인 경우 -> int()로 변환 후 -1을 하여 현재 화면(current) 인덱스로 매칭
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(curr_ids):
                matched_ids.append(curr_ids[idx])
        else:
            # 숫자가 아닌 문자열(이름)인 경우 -> 전체 누적 이름(all_names) 목록에서 탐색
            for idx, name in enumerate(all_names):
                if target in name or name in target:
                    matched_ids.append(all_ids[idx])

    if not matched_ids and curr_ids:
        matched_ids.append(curr_ids[0])
        print("오류: 매치되는 정책없음")
    
    cypher_query = """
    MATCH (p:Policy) WHERE p.servId IN $target_ids
    MATCH (p)-[:HAS_INFO]->(c:Chunk)
    RETURN p.servId AS id, p.servNm AS title, c.type AS type, c.content AS content
    """
    
    records = graph.query(cypher_query, params={"target_ids": matched_ids})
    
    if not records:
        return {"search_results": "해당 정책의 상세 정보를 찾을 수 없습니다."}

    details_by_policy = {}
    for r in records:
        pid = r['id']
        if pid not in details_by_policy:
            details_by_policy[pid] = {"title": r['title'], "chunks": []}
        details_by_policy[pid]["chunks"].append(f"■ {r['type']}\n{r['content']}")

    # 상세 정보 텍스트 가공
    result_texts = []
    for pid, data in details_by_policy.items():
        text = f"[{data['title']}] 상세 정보\n\n" + "\n\n".join(data['chunks']) + "\n" + "="*40
        result_texts.append(text)
        
  
    return {"search_results": "\n\n".join(result_texts)}


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
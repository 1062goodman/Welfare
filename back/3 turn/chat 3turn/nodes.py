import os
import re
from dotenv import load_dotenv, find_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_upstage import ChatUpstage
from langchain_upstage.embeddings import UpstageEmbeddings

from state import AgentState, IntentClassification, ConditionExtraction, TargetResolution
from prompts import (
    INTENT_SYSTEM_PROMPT, 
    RESOLVE_SYSTEM_PROMPT,
    ANSWER_SYSTEM_PROMPT, 
    EXTRACT_SYSTEM_PROMPT,
    GENERAL_CHAT_PROMPT, 
    ASK_DETAILS_PROMPT,
    SUMMERIZE_SYSTEM_PROMPT
)

# ---------------------------------------------------------
# LLM 
load_dotenv(find_dotenv())
api_key=os.getenv('UPSTAGE_API_KEY')

#선요약
summarize_llm = ChatUpstage(model="solar-mini",timeout=60, max_retries=1, temperature=0)

#의도분류
llm = ChatUpstage(model="solar-pro", timeout=60, max_retries=1, temperature=0)
structured_llm = llm.with_structured_output(IntentClassification)

#대화
chat_llm = ChatUpstage(model="solar-pro",timeout=60, max_retries=1, temperature=0)

#임베딩 모델
query_emb_model = UpstageEmbeddings(
    api_key=api_key,
    model="solar-embedding-1-large-query",
    timeout=60
)
#db연결
graph = Neo4jGraph()


# --------------------------------------------------------- 
# 의도 분류 라우팅

# 의도 분류 시스템 프롬프트 

intent_prompt = ChatPromptTemplate.from_messages([
    ("system", INTENT_SYSTEM_PROMPT),
    ("placeholder", "{messages}") # 이전 대화 기록
])

# 프롬프트와 LLM 체인 연결
intent_chain = intent_prompt | structured_llm

# 조건 추출 체인
extract_prompt = ChatPromptTemplate.from_messages([
    ("system", EXTRACT_SYSTEM_PROMPT),
    ("placeholder", "{messages}")
])
extract_chain = extract_prompt | llm.with_structured_output(ConditionExtraction)


def classify_intent_node(state: AgentState):
    result = None
    for _ in range(2):
        try:
            result = intent_chain.invoke({"messages": state["messages"]})
        except Exception as e:
            print(f"의도 분류 호출 실패: {e}")
        if result is not None:
            break
    if result is None:
        result = IntentClassification(intent="복지검색", reasoning="구조화 출력 실패, 기본값 적용")

    intent = result.intent
    if intent == "상세요구" and not state.get("recommendation_history"):
        intent = "복지검색"   # 보여준 목록이 없으면 상세요구 불가 (LLM 호출 없이 강등)

    print(f"분석 결과: {intent} (이유: {result.reasoning})\n\n")
    return {"intent": intent, "target_policy": []}
    


resolve_prompt = ChatPromptTemplate.from_messages([
    ("system", RESOLVE_SYSTEM_PROMPT),
    ("placeholder", "{messages}")
])
resolve_chain = resolve_prompt | llm.with_structured_output(TargetResolution)


def resolve_target_node(state: AgentState):
    history = state.get("recommendation_history", [])
    current_names = state.get("current_recommended_names", [])
    all_names = state.get("recommended_names", [])

    history_str = ""
    for turn_idx, names in enumerate(history):
        tag = " (가장 최근 = 현재 목록)" if turn_idx == len(history) - 1 else ""
        history_str += f"[{turn_idx+1}번째 검색 결과{tag}]\n"
        for i, name in enumerate(names):
            history_str += f"  {i+1}. {name}\n"
    current_names_str = "\n".join(f"{i+1}. {n}" for i, n in enumerate(current_names)) or "없음"

    result = None
    for _ in range(2):
        try:
            result = resolve_chain.invoke({
                "messages": state["messages"],
                "current_recommendations": current_names_str,
                "search_history": history_str or "없음",
            })
        except Exception as e:
            print(f"대상 지목 호출 실패: {e}")
        if result is not None:
            break

    def valid(t):
        if t.isdigit():
            return 0 < int(t) <= len(current_names)
        return any(t in n or n in t for n in all_names)

    targets = [t for t in (result.target_policy if result else []) if valid(t)]
    intent = "상세요구" if targets else "복지검색"   # 못 찾으면 새 검색으로 강등

    print(f"대상 지목: {targets} (이유: {result.reasoning if result else '호출 실패'})\n\n")
    return {"intent": intent, "target_policy": targets}


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



#---------------------------------------조건 추출

def extract_conditions_node(state: AgentState):
    result = None
    for _ in range(2):
        try:
            result = extract_chain.invoke({"messages": state["messages"]})
        except Exception as e:
            print(f"조건 추출 호출 실패: {e}")
        if result is not None:
            break
    if result is None:
        result = ConditionExtraction(reasoning="구조화 출력 실패, 기본값 적용")

    def merge_condition(prev, add, remove):
        return list((set(prev) | set(add)) - set(remove))   

    target_group = merge_condition(state.get("target_group", []), result.target_group_add, result.target_group_remove)
    theme = merge_condition(state.get("theme", []), result.theme_add, result.theme_remove)

    life_cycle_value = result.life_cycle
    if life_cycle_value == "임신·출산":
        life_cycle_value = "임신 · 출산"
    life_cycle = [life_cycle_value] if life_cycle_value is not None else state.get("life_cycle", [])



    search_query = result.search_query.strip() or state.get("current_query", "")
    filled_slots_count = sum(1 for slot in [life_cycle, target_group, theme] if slot)

    final_intent = "검색가능" if (result.topic_given or filled_slots_count >= 1) else "조건부족"

    print(f"분석 결과: {final_intent} (이유: {result.reasoning})")
    print(f"검색 질의: {search_query} (topic_given: {result.topic_given})")
    print(f"추출된 조건: 생애({life_cycle}), 가구({target_group}), 주제({theme})")
    print("\n\n")

    return {
        "intent": final_intent,
        "search_query": search_query,
        "life_cycle": life_cycle,
        "target_group": target_group,
        "theme": theme,
    }


# --------------------------------------------
# 검색

VEC_TOP_K = 30
VEC_THRESHOLD = 0.63
SLOT_BOOST=0.03
RESULT_LIMIT = 5
CHUNKS_PER_POLICY = 2
CHUNK_MAX_CHARS = 1200

def execute_search_node(state: AgentState):
    print("db 검색")

    query_text = state.get("search_query") or state["current_query"]
    life_cycle = state.get("life_cycle", [])
    target_group = state.get("target_group", [])
    theme = state.get("theme", [])

    query_embedding = query_emb_model.embed_query(query_text)

    cypher_vec = """
    CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $query_embedding)
        YIELD node AS c, score AS vec_score
    MATCH (p:Policy)-[:HAS_INFO]->(c)
    WITH p, max(vec_score) AS max_score,
         collect({type: c.type, content: c.content, score: vec_score}) AS hits
    WHERE max_score >= $threshold
    RETURN p.servId AS id, p.servNm AS title, p.servDgst AS digest,
           [(p)-[:MANAGED_BY]->(d:Department) | d.name][0] AS department,
           [(p)-[:PROVIDES]->(s:SupportType) | s.name][0] AS support_type,
           max_score AS score, hits,
           [(p)-[:TARGETS_AGE]->(l:LifeCycle) | l.name] AS life_cycles,
           [(p)-[:TARGETS_GROUP]->(t:TargetGroup) | t.name] AS target_groups,
           [(p)-[:RELATES_TO]->(th:Theme) | th.name] AS themes
    """
    records = graph.query(cypher_vec, params={
        "k": VEC_TOP_K,
        "query_embedding": query_embedding,
        "threshold": VEC_THRESHOLD,
    })

    # 조건이 일치하는 슬롯 하나당 가산점 (필터가 아니라 순위 보정)
    def boosted(r):
        matched = (bool(set(life_cycle) & set(r["life_cycles"]))
                   + bool(set(target_group) & set(r["target_groups"]))
                   + bool(set(theme) & set(r["themes"])))
        return r["score"] + SLOT_BOOST * matched

    records = sorted(records, key=boosted, reverse=True)[:RESULT_LIMIT]

    if not records:
        formatted_results = "조건에 맞는 복지 정책을 찾지 못했습니다."
        rec_ids, rec_names = [], []
    else:
        result_texts, rec_ids, rec_names = [], [], []
        for i, record in enumerate(records):
            rec_ids.append(record["id"])
            rec_names.append(record["title"])

            # 벡터가 찾은 청크 중 점수 높은 순, 같은 type은 1개만
            seen, parts = set(), []
            for h in sorted(record["hits"], key=lambda h: h["score"], reverse=True):
                if h["type"] in seen:
                    continue
                seen.add(h["type"])
                parts.append(f"■ {h['type']}\n{(h['content'] or '')[:CHUNK_MAX_CHARS]}")
                if len(parts) >= CHUNKS_PER_POLICY:
                    break
            body = "\n\n".join(parts) if parts else f"- 요약: {record['digest']}"

            result_texts.append(
                f"[{i+1}순위] 정책명: {record['title']} (Score: {record['score']:.4f})\n"
                f"- 담당부처: {record.get('department') or '정보없음'}\n"
                f"- 제공유형: {record.get('support_type') or '정보없음'}\n"
                f"{body}\n{'-' * 30}"
            )
        formatted_results = "\n".join(result_texts)
        print(f"{len(records)}개 정책 검색: {rec_names}")

    return {
        "search_results": formatted_results,
        "recommended_ids": rec_ids,
        "recommended_names": rec_names,
        "current_recommended_ids": rec_ids,
        "current_recommended_names": rec_names,
        "ask_count": 0,
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

    print(f"[detail] targets={targets}, matched_ids={matched_ids}, 가져온 정책={[d['title'] for d in details_by_policy.values()]}")
    
    # 상세 정보 텍스트 가공
    result_texts = []
    for pid, data in details_by_policy.items():
        text = f"[{data['title']}] 상세 정보\n\n" + "\n\n".join(data['chunks']) + "\n" + "="*40
        result_texts.append(text)
        
  
    return {
        "search_results": "\n\n".join(result_texts),
        "detail_titles": [d["title"] for d in details_by_policy.values()],
    }



# --------------------------------------------
# 답변생성
def generate_answer_node(state: AgentState):
    print("답변 생성")
    
    messages = state["messages"] 
    search_results = state.get("search_results", "검색 결과가 없습니다.")

    intent = state.get("intent", "")

    if search_results.startswith("조건에 맞는 복지 정책을 찾지 못했습니다"):
        msg = "조건에 맞는 정책을 찾지 못했습니다. 상황을 조금 다르게 말씀해 주시면 다시 찾아볼게요."
        return {"messages": [AIMessage(content=msg)], "recommendation_history": [[]]}
    if search_results.startswith(("이전에 추천해", "해당 정책의 상세 정보")):
        return {"messages": [AIMessage(content=search_results)]}
    
    if intent == "상세요구":
        guide = "사용자가 선택한 정책의 [상세 정보]를 제공 중입니다. 정보를 누락하지 말고 상세하고 친절하게 정리해 주세요."
    else:
        guide = ("여러 정책의 [목록과 요약]을 제공 중입니다. 사용자가 신청 방법, 지원 대상, 지원 내용 등 특정 정보를 물었다면 "
                 "그 정보를 먼저 답하세요. 요약하여 소개한 뒤 '더 자세히 알고 싶은 정책이 있다면 번호나 이름을 말씀해 주세요'라고 유도하세요.")

    if intent == "상세요구" and state.get("detail_titles"):
        titles = ", ".join(state["detail_titles"])
        messages = messages[:-1] + [HumanMessage(
            content=f"{messages[-1].content}\n[시스템 확인: 이 질문의 대상 정책은 '{titles}'입니다]"
        )]


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


    if intent != "상세요구":   # 목록을 보여준 턴: 화면에 나온 순서로 갱신
        norm = lambda s: re.sub(r"\s+", "", s)
        text, seen, shown = norm(response.content), set(), []
        for pid, name in zip(state.get("current_recommended_ids", []), state.get("current_recommended_names", [])):
            pos = text.find(norm(name))
            if pos >= 0 and name not in seen:
                seen.add(name); shown.append((pos, pid, name))
        if shown:
            shown.sort()
            names = [n for _, _, n in shown]
            return {"messages": [response],
                    "current_recommended_ids": [i for _, i, _ in shown],
                    "current_recommended_names": names,
                    "recommendation_history": [names]}
        return {"messages": [response],
                "recommendation_history": [state.get("current_recommended_names", [])]}
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




def ask_for_details_node(state: AgentState):
    print("부족한 조건 묻기")
    
    response = (ChatPromptTemplate.from_messages([
        ("system", ASK_DETAILS_PROMPT),
        MessagesPlaceholder(variable_name="messages")
    ]) | chat_llm).invoke({"messages": state["messages"]})
    return {"messages": [response], "ask_count": state.get("ask_count", 0) + 1}
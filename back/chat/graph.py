from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import AgentState
from nodes import (
    pre_summarize_node, 
    classify_intent_node,
    general_chat_node,
    ask_for_details_node,
    execute_search_node,
    execute_detail_search_node,
    generate_answer_node,
    block_attack_node)

# ---------------------------------------------------------
# 라우팅

def route_by_intent(state: AgentState) -> str:
    """판별된 의도(intent)에 따라 이동할 다음 노드의 이름을 반환합니다."""
    intent = state.get("intent")
    
    if intent == "일상대화":
        return "general_chat"
    elif intent == "조건부족":
        return "ask_for_details"
    elif intent == "검색가능":
        return "execute_search"
    elif intent == "상세요구":
        return "execute_detail_search"
    elif intent == "프롬프트공격":
            return "block_attack"
    
    # 기본값 일상 대화
    return "general_chat"

# ---------------------------------------------------------
# 랭그래프

workflow = StateGraph(AgentState)

# 노드 등록
workflow.add_node("pre_summarize", pre_summarize_node)
workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("general_chat", general_chat_node)
workflow.add_node("ask_for_details", ask_for_details_node)
workflow.add_node("execute_search", execute_search_node)
workflow.add_node("execute_detail_search", execute_detail_search_node)
workflow.add_node("generate_answer", generate_answer_node)
workflow.add_node("block_attack", block_attack_node)


# 시작점 설정 (의도 분석)
workflow.add_edge(START, "pre_summarize")

# 조건부 엣지
workflow.add_conditional_edges(
    "classify_intent",
    route_by_intent
)

# 일반 엣지 (쿼리 요약->의도분석)
workflow.add_edge("pre_summarize", "classify_intent")

# 일반 엣지 (검색 ->답변 생성)
workflow.add_edge("execute_search", "generate_answer")
workflow.add_edge("execute_detail_search", "generate_answer")

# 종료점 (답변이 출력되는 노드들은 끝나면 시스템 대기 상태로)
workflow.add_edge("general_chat", END)
workflow.add_edge("ask_for_details", END)
workflow.add_edge("generate_answer", END)
workflow.add_edge("block_attack", END)

# 최종 앱으로 컴파일
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
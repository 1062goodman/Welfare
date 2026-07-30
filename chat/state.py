import operator
from pydantic import BaseModel, Field
from typing import TypedDict, List, Annotated, Literal, Dict, Any
from langchain_core.messages import BaseMessage



# ---------------------------------------------------------출력상태 정의 

class IntentClassification(BaseModel):
    intent: Literal["일상대화", "조건부족", "검색가능", "상세요구", "프롬프트공격"] = Field(
        description="사용자의 질문 의도를 분류합니다."
    )
    conditions: Dict[str, Any] = Field(
        default_factory=dict,
        description="검색가능일 경우, 추출된 조건들 (예: {'생애주기': '청년', '키워드': '퇴사, 3개월'})"
    )
    target_policy: str = Field(
        default="",
        description="상세요구일 경우, 사용자가 지목한 정책의 이름이나 번호 (예: '1번', '첫번째', '햇살론')"
    )
    reasoning: str = Field(
        description="해당 의도로 분류한 논리적인 이유 (내부 확인용)"
    )


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add] # Annotated와 operator.add를 사용하면, 이전 대화 기록에 새 메시지가 계속 누적(append)됩니다.
    current_query: str
    intent: str # LLM이 판단한 의도 (일상대화 / 조건부족 / 검색가능)
    conditions: dict # LLM이 뽑아낸 검색 조건 딕셔너리
    target_policy: str
    search_results: str # Neo4j DB에서 검색해 온 최종 정책 데이터

    recommended_ids: List[str]   #찾아온 정책 기억
    recommended_names: List[str]
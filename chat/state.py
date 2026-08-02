import operator
from pydantic import BaseModel, Field
from typing import TypedDict, List, Annotated, Literal, Dict, Any
from langchain_core.messages import BaseMessage



# ---------------------------------------------------------출력상태 정의 

class IntentClassification(BaseModel):
    intent: Literal["일상대화", "조건부족", "검색가능", "상세요구", "프롬프트공격"] = Field(
        description="사용자의 질문 의도를 분류합니다."
    )
    conditions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="추출된 슬롯 필링 조건들 (예: {'생애주기': ['노년'], '가구상황': ['장애인']})"
    )

    search_keywords: List[str] = Field(
        default_factory=list,
        description="질문에서 추출한 핵심 복지/정책 관련 명사들 (예: ['장애인', '연금', '생활비']). 모호하면 빈 리스트 반환."
    )
    #유추 정책명
    policy_names: List[str] = Field(
        default_factory=list,
        description="사용자가 언급했거나 유추할 수 있는 복지 정책의 이름들 (예: ['장애인연금', '장애수당'])"
    )
    #생애주기
    life_cycle: List[Literal["임신·출산", "영유아", "아동", "청소년", "청년", "중장년", "노년"]] = Field(
        default_factory=list,
        description="질문에서 파악된 생애주기 조건"
    )
    #상황
    target_group: List[Literal["저소득", "장애인", "한부모·조손", "다자녀", "다문화·탈북민", "보훈대상자"]] = Field(
        default_factory=list,
        description="질문에서 파악된 가구상황 조건"
    )
    #주제
    theme: List[Literal["신체건강", "정신건강", "생활지원", "주거", "일자리", "문화·여가", "안전·위기", "임신·출산", "보육", "교육", "입양·위탁", "보호·돌봄", "서민금융", "법률", "에너지"]] = Field(
        default_factory=list,
        description="질문에서 파악된 관심주제 조건"
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

    policy_names: List[str]
    life_cycle: List[str]
    target_group: List[str]
    theme: List[str]

    target_policy: str
    search_results: str # Neo4j DB에서 검색해 온 최종 정책 데이터

    recommended_ids: List[str]   #찾아온 정책 기억
    recommended_names: List[str]
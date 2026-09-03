import operator
from pydantic import BaseModel, Field
from typing import TypedDict, List, Annotated, Literal, Dict, Any
from langchain_core.messages import BaseMessage



# ---------------------------------------------------------출력상태 정의 

class IntentClassification(BaseModel):
    intent: Literal["일상대화", "조건부족", "검색가능", "상세요구", "프롬프트공격"] = Field(
        description="사용자의 질문 의도를 분류합니다."
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
        description="질문에서 파악된 생애주기 조건. 사용자가 특정 연령이나 생애주기를 명시하지 않았다면 절대로 유추하지 말고 반드시 빈 리스트 [] 를 반환할 것."
    )
    #상황
    target_group: List[Literal["저소득", "장애인", "한부모·조손", "다자녀", "다문화·탈북민", "보훈대상자"]] = Field(
        default_factory=list,
        description="질문에서 파악된 가구상황 조건"
    )
    #주제
    theme: List[Literal["신체건강", "정신건강", "생활지원", "주거", "일자리", "문화·여가", "안전·위기", "임신·출산", "보육", "교육", "입양·위탁", "보호·돌봄", "서민금융", "법률", "에너지"]] = Field(
        default_factory=list,
        description="질문에서 파악된 주제 조건"
    )
    #상세요구 타겟정책
    target_policy: List[str] = Field(
        default_factory=list,
        description="의도가 '상세요구'일 경우, 사용자가 지목한 정책의 이름이나 번호를 추출할 것. 단 사용자가 지목한 번호의 경우 '1번', '첫번째' 등 수식어를 제외하고 오직 순수 숫자 문자열만 추출할 것 (예: ['1', '2', '국민연금', '5', '청년퇴직금지원'] ) "
    )
    reasoning: str = Field(
        description="해당 의도로 분류한 논리적인 이유 (내부 확인용)"
    )


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add] # Annotated와 operator.add를 사용하면, 이전 대화 기록에 새 메시지가 계속 누적(append)됩니다.
    current_query: str

    intent: str # LLM이 판단한 의도 (일상대화 / 조건부족 / 검색가능)
    search_keywords: List[str]
    policy_names: List[str]
    life_cycle: List[str]
    target_group: List[str]
    theme: List[str]

    #검색 누적 보관함
    search_results: str # Neo4j DB에서 검색해 온 최종 정책 데이터 
    recommended_ids: Annotated[List[str], operator.add]   #찾아온 정책 기억
    recommended_names: Annotated[List[str], operator.add]

    current_recommended_ids: List[str]
    current_recommended_names: List[str]



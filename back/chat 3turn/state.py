import operator
from pydantic import BaseModel, Field
from typing import TypedDict, List, Annotated, Literal, Optional
from langchain_core.messages import BaseMessage



# ---------------------------------------------------------출력상태 정의 

class IntentClassification(BaseModel):
    reasoning: str = Field(
            description="가장 먼저 작성. 이 입력을 해당 의도로 분류한 이유를 간결하게. 이 판단에 맞춰 intent를 채울 것."
    )
    intent: Literal["일상대화", "복지검색", "상세요구", "프롬프트공격"] = Field(
        description="사용자의 질문 의도를 분류합니다."
    )

    
class TargetResolution(BaseModel):
    reasoning: str = Field(
        description="가장 먼저 작성. '차수=…(근거 표현), 번호=…, 정책명=…' 순서로 적을 것. 이 판단에 맞춰 target_policy를 채울 것."
    )
    target_policy: List[str] = Field(
        default_factory=list,
        description="가장 최근 검색 결과의 번호로 지목하면 숫자 문자열만 (예: ['2']). "
                    "과거 검색 결과나 이름으로 지목하면 이력에 적힌 정책명 그대로. "
                    "이력에 없는 대상이면 빈 리스트."
    )


class ConditionExtraction(BaseModel):

    reasoning: str = Field(
        description="가장 먼저 작성, 인용 위주로 간결하게. ① 이번 발화와 이전 대화에서 검색할 주제가 무엇인지 "
                    "② 생애주기·가구상황·주제를 채운다면 근거가 되는 사용자의 발화 인용 (인용할 문장이 없으면 그 조건은 비울 것). "
                    "이 판단에 맞춰 아래 필드를 채울 것."
    )
    search_query: str = Field(
        default="",
        description="이전 대화와 이번 질문을 합쳐, 그것만 읽어도 뜻이 통하는 한두 문장의 검색 질의. "
                    "이번 질문이 이미 완결된 문장이면 거의 그대로 쓰고, 후속 질문이면 이전 대화의 주제를 합칠 것. "
                    "정책명이 언급되면 그대로 포함하고, 대화에 없는 내용은 지어내지 말 것."
    )
    topic_given: bool = Field(
        default=True,
        description="이번 발화와 이전 대화를 합쳐서 검색할 구체적 주제(특정 정책명, 분야, 자기 상황 중 하나)가 있으면 true, "
                    "'받을 수 있는 지원금 있어?'처럼 아무 단서도 없으면 false."
    )
    #생애주기
    life_cycle: Optional[Literal["임신·출산", "영유아", "아동", "청소년", "청년", "중장년", "노년"]] = Field(
        default=None,
        description="이번 발화에서 파악된 화자 본인의 생애주기. 언급 없으면 None(이전 값 유지), "
                    "새로 언급되면 그 값으로 교체(이전 값 무효)."
    )
    #상황
    target_group_add: List[Literal["저소득", "장애인", "한부모·조손", "다자녀", "다문화·탈북민", "보훈대상자"]] = Field(default_factory=list)
    target_group_remove: List[Literal["저소득", "장애인", "한부모·조손", "다자녀", "다문화·탈북민", "보훈대상자"]] = Field(default_factory=list)
    #주제
    theme_add: List[Literal["신체건강", "정신건강", "생활지원", "주거", "일자리", "문화·여가", "안전·위기", "임신·출산", "보육", "교육", "입양·위탁", "보호·돌봄", "서민금융", "법률", "에너지"]] = Field(default_factory=list)
    theme_remove: List[Literal["신체건강", "정신건강", "생활지원", "주거", "일자리", "문화·여가", "안전·위기", "임신·출산", "보육", "교육", "입양·위탁", "보호·돌봄", "서민금융", "법률", "에너지"]] = Field(default_factory=list)
    

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add] # Annotated와 operator.add를 사용하면, 이전 대화 기록에 새 메시지가 계속 누적(append)됩니다.
    current_query: str

    intent: str # LLM이 판단한 의도 (일상대화 / 조건부족 / 검색가능 / 상세요구 / 프롬프트공격)
    search_query: str 
    life_cycle: List[str]
    target_group: List[str]
    theme: List[str]

    ask_count: int

    detail_titles: List[str]

    #검색 누적 보관함
    search_results: str # Neo4j DB에서 검색해 온 최종 정책 데이터 
    recommended_ids: Annotated[List[str], operator.add]   #찾아온 정책 기억
    recommended_names: Annotated[List[str], operator.add]

    target_policy: List[str] 
    current_recommended_ids: List[str]
    current_recommended_names: List[str]

    recommendation_history: Annotated[List[List[str]], operator.add]



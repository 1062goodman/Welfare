import operator
from pydantic import BaseModel, Field
from typing import TypedDict, List, Annotated, Literal, Optional
from langchain_core.messages import BaseMessage



# ---------------------------------------------------------출력상태 정의 

class IntentClassification(BaseModel):
    reasoning: str = Field(
            description="가장 먼저 작성. 이 입력을 해당 의도로 분류한 이유를 간결하게. "
                    "상세요구라면 [추천 목록]/[검색 이력]의 어떤 항목을 가리키는지 인용. 이 판단에 맞춰 아래 필드를 채울 것."
        )
    intent: Literal["일상대화", "복지검색", "상세요구", "프롬프트공격"] = Field(
        description="사용자의 질문 의도를 분류합니다."
    )

    
    #상세요구 타겟정책
    target_policy: List[str] = Field(
        default_factory=list,
        description="""의도가 '상세요구'일 경우, 사용자가 지목한 정책의 이름이나 번호를 추출할 것.
사용자가 방금 보여준 목록(직전 턴)에서 번호로 지목하면, 순수 숫자 문자열만 추출하세요 (예: '1번' → '1').
사용자가 '처음', '아까', '이전에' 등 과거 시점의 목록을 가리키면, [지금까지의 검색 이력]을 참고하여 
해당하는 정책명을 그대로 추출하세요 (숫자 아님).
(예: ['1', '2', '국민연금', '5', '청년퇴직금지원'])"""
    )
    


class ConditionExtraction(BaseModel):

    reasoning: str = Field(
            description="가장 먼저 작성. ① 사용자가 정책·제도 이름으로 보이는 표현을 말했는가(말했다면 원문 인용) "
                        "② 조건을 채운다면 근거가 되는 발화 인용. 이 판단에 맞춰 아래 필드를 채울 것."
        )
    
    search_keywords: List[str] = Field(
        default_factory=list,
        description="정책명이 아닌 일반 명사만 (예: ['연금', '생활비']). 정책명은 여기 넣지 말고 policy_names에 넣을 것. 없으면 빈 리스트."
    )
    #유추 정책명
    policy_names: List[str] = Field(
        default_factory=list,
        description="""사용자가 언급했거나 유추할 수 있는 복지 정책의 이름들을 추출하세요.
    실제로 그런 정책이 존재하는지 여부는 판단하지 마세요 — 정책의 존재 여부 확인은 이후 검색 시스템이 담당합니다. 
    당신의 역할은 오직 "사용자가 특정 정책을 지칭하고 있는가, 그렇다면 어떤 이름으로 보이는가"를 추출하는 것입니다.
    
    - 이름을 정확히 기억하지 못하지만 특정 제도를 가리키는 표현("~인가 뭔가 있다던데")을 썼을 때만 후보 정책명을 유추하세요.
      자기 상황을 말하며 지원을 찾는 경우는 유추하지 말고 빈 리스트를 반환하세요.
      (예: "장애인한테 주는 연금인가 뭔가가 있다던데" → ["장애인연금", "장애수당"])
    - 사용자가 특정 정책명을 언급했지만, 그런 이름의 정책이 실제로 존재하는지 확신할 수 없어도 그대로 추출하세요. 
      당신이 모르는 정책일 수도, 사용자가 이름을 잘못 기억했을 수도, 아예 존재하지 않는 이름일 수도 있지만, 
      이를 판단하지 말고 언급된 그대로 추출하세요.
      (예: "청년희망꿈나래지원금이라는 거 신청하고 싶어요" → ["청년희망꿈나래지원금"])
    - 정책명이 전혀 언급되지 않았고 유추할 단서도 없다면 빈 리스트를 반환하세요.
    """
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

    intent: str # LLM이 판단한 의도 (일상대화 / 조건부족 / 검색가능)
    search_keywords: List[str]
    policy_names: List[str]
    life_cycle: List[str]
    target_group: List[str]
    theme: List[str]

    ask_count: int
    is_narrow: bool # 조건이 좁혀졌는가?
    narrow_target_slot: str       # 다음에 물어보면 가장 효율적인 슬롯 ("life_cycle"/"target_group"/"theme")
    answer_notice: str  

    #검색 누적 보관함
    search_results: str # Neo4j DB에서 검색해 온 최종 정책 데이터 
    recommended_ids: Annotated[List[str], operator.add]   #찾아온 정책 기억
    recommended_names: Annotated[List[str], operator.add]

    target_policy: List[str] 
    current_recommended_ids: List[str]
    current_recommended_names: List[str]

    recommendation_history: Annotated[List[List[str]], operator.add]



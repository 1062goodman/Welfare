import operator
from pydantic import BaseModel, Field
from typing import TypedDict, List, Annotated, Literal
from langchain_core.messages import BaseMessage



# ---------------------------------------------------------출력상태 정의 

class  SimpleExtraction(BaseModel):
    earch_keywords: List[str] = Field(default_factory=list),
    policy_names: List[str] = Field(default_factory=list),
    life_cycle: List[Literal["임신·출산", "영유아", "아동", "청소년", "청년", "중장년", "노년"]] = Field(default_factory=list)
    target_group: List[Literal["저소득", "장애인", "한부모·조손", "다자녀", "다문화·탈북민", "보훈대상자"]] = Field(default_factory=list)
    theme: List[Literal["신체건강", "정신건강", "생활지원", "주거", "일자리", "문화·여가", "안전·위기", "임신·출산", "보육", "교육", "입양·위탁", "보호·돌봄", "서민금융", "법률", "에너지"]] = Field(default_factory=list)



class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add] # Annotated와 operator.add를 사용하면, 이전 대화 기록에 새 메시지가 계속 누적(append)됩니다.
    current_query: str

    intent: str # LLM이 판단한 의도 (일상대화 / 조건부족 / 검색가능)
    search_keywords: List[str]
    policy_names: List[str]
    life_cycle: List[str]
    target_group: List[str]
    theme: List[str]

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


from langchain_upstage import ChatUpstage # 챗 모델
import os

from langchain_core.tools import tool


# from langchain_core.messages import HumanMessage

from dotenv import load_dotenv
load_dotenv()


api_key = os.getenv('solarkey')
base_url = "https://api.upstage.ai/v1"
llm_model = "solar-pro"


solar_llm = ChatUpstage(
    api_key=api_key,
    model = llm_model
)


@tool
def get_weather(location: str) -> str:
    """주어진 지역의 현재 날씨를 알려주는 도구입니다."""
    # 실제로는 기상청 API 등을 호출하는 코드가 들어갑니다.
    if location == "순천":
        
        return "맑고 화창함, 25도"
    return "알 수 없는 날씨"

llm_with_tools = solar_llm.bind_tools([get_weather])

query = "오늘 순천 날씨 어때?"
response = llm_with_tools.invoke(query)

print(response.tool_calls)
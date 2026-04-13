import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('datakey')

url = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001"

params = {
    'serviceKey': api_key,
    'callTp': 'L',
    'pageNo': '1',
    'numOfRows': '10', #기본값 10 최대 500
    'srchKeyCode' : '003' #001 제목, 002 내용, 003 제목+내용
}

try:
    response = requests.get(url, params=params)
    
    print("상태 코드:", response.status_code)
    print("결과 데이터:\n", response.text)

except Exception as e:
    print("요청 중 에러 발생:", e)
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
    'numOfRows': '500', #기본값 10 최대 500
    'srchKeyCode' : '003' #001 제목, 002 내용, 003 제목+내용
}

try:
    response = requests.get(url, params=params)
    
    print("상태 코드:", response.status_code)

except Exception as e:
    print("요청 중 에러 발생:", e)


try:
    with open('example.xml', 'w', encoding='utf-8') as f :
        f.write(response.text)
except Exception as E:
    print(f"xml파일 생성중 에러: {E}")
import requests
import os
import math
import json
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('datakey2')

url = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfarelist"

NUM_OF_ROWS = 500

def fetch_page(page_no, num_of_rows=NUM_OF_ROWS):
    params = {
        'serviceKey': api_key,
        'callTp': 'L',
        'pageNo': str(page_no),
        'numOfRows': str(num_of_rows),
        'srchKeyCode': '003'
    }
    response = requests.get(url, params=params)
    response.raise_for_status()  # 상태코드 에러시 예외 발생
    return response.text


first_page_xml = fetch_page(1)
root = ET.fromstring(first_page_xml)

total_count = int(root.findtext('.//totalCount'))
total_pages = math.ceil(total_count / NUM_OF_ROWS)
print(f"전체 건수: {total_count}, 총 페이지 수: {total_pages}")

combined_root = ET.Element("response")
servList_items = root.findall('.//servList')
for page_no in range(2, total_pages + 1):
    page_xml = fetch_page(page_no)
    page_root = ET.fromstring(page_xml)
    for item in page_root.findall('.//servList'):
        combined_root.append(item)
    print(f"{page_no}페이지 수집 완료 (누적 {len(combined_root)}건)")

# 4) 하나의 완전한 XML로 저장 (덮어쓰기 한 번만)
tree = ET.ElementTree(combined_root)
ET.indent(tree, space="  ")  # 보기 좋게 들여쓰기 (Python 3.9+)
tree.write('example2.xml', encoding='utf-8', xml_declaration=True)
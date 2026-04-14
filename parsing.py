#****************************************************
#****추후에는 파싱과 json 파일 생성을 따로 만들어서 관리
#****************************************************

import xml.etree.ElementTree as ET
import json

try:
    tree = ET.parse('example.xml')
    root = tree.getroot()
except Exception as E:
    print(f"파싱중 에러: {E}")


if root.find('resultMessage').text != 'SUCCESS':
    raise Exception("resultMessage가 SUCCESS가 아닙니다.")


data_list = []
for serv in root.findall('servList'):
    item_dict ={}
    for child in serv:
        item_dict[child.tag] = child.text
    data_list.append(item_dict)

try:
    with open('DataList.json', 'w', encoding='utf-8') as f :
        json.dump(data_list, f, indent=4,ensure_ascii=False)
except Exception as E:
    print(f"json파일 생성중 에러: {E}")



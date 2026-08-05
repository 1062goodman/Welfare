from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time 
import re
import json 
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 

chrome_options = Options()
chrome_options.add_argument("--ignore-certificate-errors") 

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

base_url = "https://www.bokjiro.go.kr/ssis-tbu/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId="
#index = "WLF00006256"





def search_detailed_info(driver, serv_id):
    url = f"https://www.bokjiro.go.kr/ssis-tbu/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId={serv_id}"
    
    result_data = {
        "target_info": "정보 없음",
        "service_content": "정보 없음",
        "apply_method": "정보 없음"
    }
    
    tabs_to_scrape = {
        "지원대상": "target_info",
        "서비스 내용": "service_content",
        "신청방법": "apply_method"
    }
    
    try:
        driver.get(url)
        time.sleep(0.1) 
        
        for tab_name, key in tabs_to_scrape.items():
            try:
                
                tab_xpath = f"//div[contains(@class, 'tabfolder-item')]//div[contains(text(), '{tab_name}')]"
                tab = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, tab_xpath)))
                driver.execute_script("arguments[0].click();", tab)

                #대기
                title_xpath = f"//div[contains(@class, 'line-tit')]//div[contains(text(), '{tab_name}')]"
                WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, title_xpath)))
        
                
                # 데이터 파싱
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # 제목 및 내용 상자 찾기
                title = next((t for t in soup.find_all(class_='line-tit') if tab_name in t.text), None)
                box = title.find_next(class_='bokjiServiceView') if title else None
                
                # 결과 추출
                if box: 
                    lis = box.find_all('li')
                    result_data[key] = "\n".join([li.text.strip() for li in lis]) if lis else box.get_text(separator="\n", strip=True)
                else:
                    result_data[key] = "내용을 찾지 못했습니다."
                    
            except Exception as e:
                result_data[key] = "탭 수집 실패"
                
        return result_data

    except Exception as e:
        return {"target_info": "접속 실패", "service_content": "접속 실패", "apply_method": "접속 실패"}




############################################## json파일 초기화
with open('DataList1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

size = len(data)

for index, item in enumerate(data):
    url = item.get("servId")

    if item.get("targrt_info") == None:

        new_data_dict = search_detailed_info(driver, url)
        item.update(new_data_dict) #데이터 업데이트

   
    # 중간저장
    if index %10 == 0:
        print(f"{index + 1}/ {size} ---- 중간 저장")
        with open('DataList1.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
   



with open('DataList1.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


driver.quit()


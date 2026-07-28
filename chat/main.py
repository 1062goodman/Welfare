import os
from dotenv import load_dotenv, find_dotenv
from langchain_core.messages import HumanMessage

# 환경변수 
load_dotenv(find_dotenv())

#
from graph import app

def run_chatbot():
    print("대화 시작되었습니다! (종료: 'q')")
    print("-" * 50)
    
    # 그래프를 순환할 초기 화물칸(상태) 세팅
    current_state = {"messages": []}
    
    while True:
        user_input = input("사용자: ")
        
        if user_input.lower() in ['q']:
            print("종료합니다.")
            break

        elif len(user_input) <= 800:
            print("글자수가 너무 많습니다.")
            continue
        # 리스트에 넣기
        current_state["messages"].append(HumanMessage(content=user_input))
        
        # LangGraph 챗봇 실행
        result_state = app.invoke(current_state)
        
       
        ai_response = result_state["messages"][-1].content
        print(f"\n답변: {ai_response}\n")
        \
        
       
        current_state["messages"] = result_state["messages"]

if __name__ == "__main__":
    run_chatbot()
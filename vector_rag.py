# 랭체인에서 제공하는 그래프 지식 저장소
from langchain_community.graphs import NetworkxEntityGraph
from langchain_community.graphs.index_creator import GraphIndexCreator
# 랭체인에서 제공하는 벡터 지식 저장소
from langchain_community.vectorstores import Chroma 



from langchain_core.documents import Document # document 형식
from langchain_community.document_loaders import JSONLoader # document json 로더


from langchain_upstage import ChatUpstage # 챗 모델
from langchain_upstage.embeddings import UpstageEmbeddings # 임베딩 모델
from langchain_core.messages import HumanMessage


import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('solarkey')
base_url = "https://api.upstage.ai/v1"
llm_model = "solar-pro"
emb_model = "solar-embedding-1-large-query"

file_path = "DataList.json"

with open(file_path, "r", encoding="utf-8") as f:
    raw_text = f.read()

loader = JSONLoader(file_path= file_path,
                    jq_schema='.[]',
                    content_key='servDgst',
                    text_content=False)







# chroma db 만들기

docs = loader.load()
print(docs[0].__dict__)
print("\n\n")
print("------------------------------")

#모델 불러오기
solar_llm = ChatUpstage(
    api_key=api_key,
    model = llm_model
)
solar_emb = UpstageEmbeddings(
    api_key=api_key,
    model = emb_model
)

def Vector():
    vector_db = Chroma.from_documents(
        documents=docs,  # 청크로 쪼갠 리스트 형태
        embedding = solar_emb,
        persist_directory= "./chroma_db"
    )

#Vector()



#===============검색======================

#db load
loaded_db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=solar_emb
)


query = "아이를 키우는데 돈이 많이 들어. 어떻게 해야할까?"

testdocs = loaded_db.similarity_search(query, k=3) # 유사도가 높은 k개 

print(f"질문: {query}\n")
for i, doc in enumerate(testdocs):
    print(f"--- 검색 결과 {i+1} ---")
    print(f"내용: {doc.page_content}")
    print(f"번호: {doc.metadata['seq_num']}")


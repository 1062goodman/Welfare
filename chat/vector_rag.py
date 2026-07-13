# 랭체인에서 제공하는 그래프 지식 저장소
from langchain_community.graphs import NetworkxEntityGraph
from langchain_community.graphs.index_creator import GraphIndexCreator
# 랭체인에서 제공하는 벡터 지식 저장소
from langchain_community.vectorstores import Chroma 



from langchain_core.documents import Document # document 형식
from langchain_community.document_loaders import JSONLoader # document json 로더



from langchain_upstage.embeddings import UpstageEmbeddings # 임베딩 모델



import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('solarkey')
emb_model = "solar-embedding-1-large-query"

file_path = "DataList.json"

with open(file_path, "r", encoding="utf-8") as f:
    raw_text = f.read()

loader = JSONLoader(file_path= file_path,
                    jq_schema='.[]',
                    content_key='servDgst',
                    text_content=False)







# chroma db 만들기

#embedding 모델 불러오기

docs = loader.load()

solar_emb = UpstageEmbeddings(
    api_key=api_key,
    model = emb_model
)

#vector db 생성
def make_Vector():
    vector_db = Chroma.from_documents(
        documents=docs,  # 청크로 쪼갠 리스트 형태
        embedding = solar_emb,
        persist_directory= "./chroma_db",
        collection_metadata={"hnsw:space": "cosine"} # 유사도 계산은 코사인으로
    )

# make_Vector()





#===============검색======================

#db load
loaded_db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=solar_emb
)


def search(query):
    ks =20
    #1 유사도 높은 순서로 k개 뽑기
    testdocs = loaded_db.similarity_search_with_score(query, k=ks) # 유사도가 높은 k개 

    for i in range(ks):
        print(f"{testdocs[i][0].page_content}: {testdocs[i][1]}\n")


search("배고파")

"""

print(f"질문: {query}\n")
for i, doc in enumerate(testdocs):
    print(f"--- 검색 결과 {i+1} ---")
    print(f"내용: {doc.page_content}")
    print(f"내용: {doc.page_content}")
    print(f"번호: {doc.metadata['seq_num']}")

"""
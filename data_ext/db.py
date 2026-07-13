#-------------------------------------------------------- 
# 노드 분리 및 document형식으로 만들기

import json
from langchain_core.documents import Document

file_path = 'DataList1.json'

with open(file_path, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

documents = []

for item in raw_data:
    
    #여러개가 있어서 리스트 형태로 분리
    life_array = [x.strip() for x in item.get("lifeArray", "").split(",") if x.strip()]
    intrs_thema_array = [x.strip() for x in item.get("intrsThemaArray", "").split(",") if x.strip()]
    trgter_indvdl_array = [x.strip() for x in item.get("trgterIndvdlArray", "").split(",") if x.strip()]
    
    
    #노드와 관계를 만들 때 사용
    metadata = {
        "servId": item.get("servId", ""),
        "servNm": item.get("servNm", ""),
        "servDgst": item.get("servDgst", ""),
        "jurMnofNm": item.get("jurMnofNm", ""),   # 부처 노드용
        "srvPvsnNm": item.get("srvPvsnNm", ""),   # 제공유형 노드용
        "lifeArray": life_array,                  # 생애주기 노드용 (리스트 형태)
        "intrsThemaArray": intrs_thema_array,     # 관심주제 노드용 (리스트 형태)
        "trgterIndvdlArray": trgter_indvdl_array  # 대상/가구유형 노드용 (리스트 형태)
    }

    #이건 벡터화하여 저장 (벡터검색으로 자신의 조건에 맞는 정책 및 서비스 찾기)
    page_content = f"""
    [정책명]: {item.get('servNm', '')}
    [한줄요약]: {item.get('servDgst', '')}
    [지원대상 상세]: {item.get('target_info', '')}
    [서비스내용 상세]: {item.get('service_content', '')}
    [신청방법 상세]: {item.get('apply_method', '')}
    """

    
    doc = Document(page_content=page_content.strip(), metadata=metadata)
    documents.append(doc)


#-------------------------------------------------------- 
#db 적재

import os
from dotenv import find_dotenv, load_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_upstage.embeddings import UpstageEmbeddings 

load_dotenv(find_dotenv())
api_key = os.getenv('solarkey')
os.environ["NEO4J_URI"] = os.getenv('NEO4J_URI')
os.environ["NEO4J_USERNAME"] = os.getenv('NEO4J_USERNAME')
os.environ["NEO4J_PASSWORD"] = os.getenv('NEO4J_PASSWORD')
os.environ["NEO4J_DATABASE"] = os.getenv('NEO4J_USERNAME')


base_url = "https://api.upstage.ai/v1"
llm_model = "solar-pro"
emb_model = "solar-embedding-1-large-passage" #passage query

solar_emb = UpstageEmbeddings(
    api_key=api_key,
    model = emb_model
)

graph = Neo4jGraph()



texts_to_embed = [doc.page_content for doc in documents]
embeddings = solar_emb.embed_documents(texts_to_embed)

# Neo4j Cypher 쿼리문 

ingestion_query = """
// 1) 정책(Policy) 중심 노드 생성 및 벡터/속성 저장
MERGE (p:Policy {servId: $metadata.servId})
SET p.servNm = $metadata.servNm,
    p.servDgst = $metadata.servDgst,
    p.page_content = $page_content,
    p.embedding = $embedding

// 2) 부처(Department) 노드 연결 (값이 있을 때만)
FOREACH (dept IN CASE WHEN $metadata.jurMnofNm <> "" THEN [$metadata.jurMnofNm] ELSE [] END |
    MERGE (d:Department {name: dept})
    MERGE (p)-[:MANAGED_BY]->(d)
)

// 3) 제공유형(SupportType) 노드 연결
FOREACH (stype IN CASE WHEN $metadata.srvPvsnNm <> "" THEN [$metadata.srvPvsnNm] ELSE [] END |
    MERGE (s:SupportType {name: stype})
    MERGE (p)-[:PROVIDES]->(s)
)

// 4) 생애주기(LifeCycle) 노드 연결 (리스트를 순회하며 여러 개 생성)
FOREACH (life IN $metadata.lifeArray |
    MERGE (l:LifeCycle {name: life})
    MERGE (p)-[:TARGETS_AGE]->(l)
)

// 5) 대상/가구유형(TargetGroup) 노드 연결
FOREACH (target IN $metadata.trgterIndvdlArray |
    MERGE (t:TargetGroup {name: target})
    MERGE (p)-[:TARGETS_GROUP]->(t)
)

// 6) 관심주제(Theme) 노드 연결
FOREACH (theme IN $metadata.intrsThemaArray |
    MERGE (th:Theme {name: theme})
    MERGE (p)-[:RELATES_TO]->(th)
)
"""


for i, doc in enumerate(documents):

    params = {
        "metadata": doc.metadata,
        "page_content": doc.page_content,
        "embedding": embeddings[i]
    }
    
    graph.query(ingestion_query, params=params)
    
    if (i + 1) % 10 == 0:
        print(f"[{i + 1} / {len(documents)}] 개 완료...")



create_index_query = """
CREATE VECTOR INDEX policy_embedding_index IF NOT EXISTS
FOR (p:Policy)
ON (p.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 4096,
  `vector.similarity_function`: 'cosine'
}}
"""
graph.query(create_index_query)

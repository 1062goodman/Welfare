#-------------------------------------------------------- 
# 노드 분리 및 document형식으로 만들기

import json
from langchain_core.documents import Document

file_path = 'DataList1.json'

with open(file_path, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)



structured_data = [] 
texts_to_embed = []

for item in raw_data:
    
    serv_nm = item.get("servNm", "")
    serv_id = item.get("servId", "")

    #여러개가 있어서 리스트 형태로 분리
    life_array = [x.strip() for x in item.get("lifeArray", "").split(",") if x.strip()]
    intrs_thema_array = [x.strip() for x in item.get("intrsThemaArray", "").split(",") if x.strip()]
    trgter_indvdl_array = [x.strip() for x in item.get("trgterIndvdlArray", "").split(",") if x.strip()]
    
    
    #노드와 관계를 만들 때 사용
    metadata = {
        "servId": serv_id,
        "servNm": serv_nm,
        "servDgst": item.get("servDgst", ""),
        "jurMnofNm": item.get("jurMnofNm", ""),   # 부처 노드용
        "srvPvsnNm": item.get("srvPvsnNm", ""),   # 제공유형 노드용
        "lifeArray": life_array,                  # 생애주기 노드용 (리스트 형태)
        "intrsThemaArray": intrs_thema_array,     # 관심주제 노드용 (리스트 형태)
        "trgterIndvdlArray": trgter_indvdl_array  # 대상/가구유형 노드용 (리스트 형태)
    }

    chunks = []
    
    # 지원대상
    if item.get("target_info"):
        # 벡터 검색 성능을 높이기 위해 정책명을 앞에 붙여줍니다.
        content = f"[정책명: {serv_nm}] 지원대상: {item.get('target_info')}"
        chunks.append({"type": "지원대상", "content": content})
        texts_to_embed.append(content)
        
    # 서비스내용
    if item.get("service_content"):
        content = f"[정책명: {serv_nm}] 서비스내용: {item.get('service_content')}"
        chunks.append({"type": "서비스내용", "content": content})
        texts_to_embed.append(content)
        
    # 신청방법
    if item.get("apply_method"):
        content = f"[정책명: {serv_nm}] 신청방법: {item.get('apply_method')}"
        chunks.append({"type": "신청방법", "content": content})
        texts_to_embed.append(content)
        
    structured_data.append({
        "metadata": metadata,
        "chunks": chunks
    })

    #이건 벡터화하여 저장 (벡터검색으로 자신의 조건에 맞는 정책 및 서비스 찾기)
    page_content = f"""
    [정책명]: {item.get('servNm', '')}
    [한줄요약]: {item.get('servDgst', '')}
    [지원대상 상세]: {item.get('target_info', '')}
    [서비스내용 상세]: {item.get('service_content', '')}
    [신청방법 상세]: {item.get('apply_method', '')}
    """

print("전처리 완료")



#-------------------------------------------------------- 
#db 적재



import os
from dotenv import find_dotenv, load_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_upstage.embeddings import UpstageEmbeddings 

load_dotenv(find_dotenv())
api_key = os.getenv('UPSTAGE_API_KEY')
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

print("연결 완료")

embeddings = solar_emb.embed_documents(texts_to_embed)

emb_index = 0
for data in structured_data:
    for chunk in data["chunks"]:
        chunk["embedding"] = embeddings[emb_index]
        emb_index += 1

print("임베딩 완료")

# Neo4j Cypher 쿼리문 

ingestion_query = """
// 1) 정책(Policy) 본체 노드 생성 (내용과 벡터가 없음!)
MERGE (p:Policy {servId: $metadata.servId})
SET p.servNm = $metadata.servNm,
    p.servDgst = $metadata.servDgst

// 2) 부처, 제공유형 등 메타데이터 연결 (기존 동일)
FOREACH (dept IN CASE WHEN $metadata.jurMnofNm <> "" THEN [$metadata.jurMnofNm] ELSE [] END |
    MERGE (d:Department {name: dept})
    MERGE (p)-[:MANAGED_BY]->(d)
)
FOREACH (stype IN CASE WHEN $metadata.srvPvsnNm <> "" THEN [$metadata.srvPvsnNm] ELSE [] END |
    MERGE (s:SupportType {name: stype})
    MERGE (p)-[:PROVIDES]->(s)
)
FOREACH (life IN $metadata.lifeArray |
    MERGE (l:LifeCycle {name: life})
    MERGE (p)-[:TARGETS_AGE]->(l)
)
FOREACH (target IN $metadata.trgterIndvdlArray |
    MERGE (t:TargetGroup {name: target})
    MERGE (p)-[:TARGETS_GROUP]->(t)
)
FOREACH (theme IN $metadata.intrsThemaArray |
    MERGE (th:Theme {name: theme})
    MERGE (p)-[:RELATES_TO]->(th)
)

// 3) 핵심! 정보 조각(Chunk) 노드 생성 및 HAS_INFO 관계로 연결
FOREACH (chk IN $chunks |
    // ID를 'WLF0000_지원대상' 형식으로 고유하게 생성
    MERGE (c:Chunk {id: $metadata.servId + '_' + chk.type})
    SET c.type = chk.type,
        c.content = chk.content,
        c.embedding = chk.embedding
    MERGE (p)-[:HAS_INFO]->(c)
)
"""

print("db적재")
for i, doc in enumerate(structured_data):
    graph.query(ingestion_query, params=data)
    if (i + 1) % 10 == 0:
        print(f"[{i + 1} / {len(structured_data)}] 정책 완료...")



create_index_query = """
CREATE VECTOR INDEX chunk_embedding_index IF NOT EXISTS
FOR (c:Chunk)
ON (c.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 4096,
  `vector.similarity_function`: 'cosine'
}}
"""

graph.query(create_index_query)




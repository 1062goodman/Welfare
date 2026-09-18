# --------------------------------------------------------
# 노드 분리 및 document 형식으로 만들기

import json
from langchain_core.documents import Document


# --------------------------------------------------------
# 파일별 변환 함수 — 서로 다른 필드 이름을 공통 형식으로 통일

def normalize_list1(item):
    """DataList1(중앙 복지 데이터) 형식을 공통 형식으로 변환"""
    life = [x.strip() for x in item.get("lifeArray", "").split(",") if x.strip()]
    theme = [x.strip() for x in item.get("intrsThemaArray", "").split(",") if x.strip()]
    target = [x.strip() for x in item.get("trgterIndvdlArray", "").split(",") if x.strip()]

    return {
        "servId": item.get("servId", ""),
        "servNm": item.get("servNm", ""),
        "servDgst": item.get("servDgst", ""),
        "jurMnofNm": item.get("jurMnofNm", ""),
        "srvPvsnNm": item.get("srvPvsnNm", ""),
        "life": life,
        "theme": theme,
        "target": target,
        "region": None,  # 중앙 데이터는 지역 없음
        "chunks_raw": {
            "지원대상": item.get("target_info", ""),
            "서비스내용": item.get("service_content", ""),
            "신청방법": item.get("apply_method", ""),
        }
    }


def normalize_list2(item):
    """DataList2(지자체 복지 데이터) 형식을 공통 형식으로 변환"""
    life = [x.strip() for x in item.get("lifeNmArray", "").split(",") if x.strip()]
    theme = [x.strip() for x in item.get("intrsThemaNmArray", "").split(",") if x.strip()]
    target = [x.strip() for x in item.get("trgterIndvdlNmArray", "").split(",") if x.strip()]

    ctpv = item.get("ctpvNm")
    sgg = item.get("sggNm") or "전체"  # 구 정보가 없으면(세종시 등) "전체"로 통일

    return {
        "servId": item.get("servId", ""),
        "servNm": item.get("servNm", ""),
        "servDgst": item.get("servDgst", ""),
        "jurMnofNm": item.get("bizChrDeptNm", ""),  # 지자체는 부서명을 담당부처처럼 사용
        "srvPvsnNm": item.get("srvPvsnNm", ""),
        "life": life,
        "theme": theme,
        "target": target,
        "region": {"ctpv": ctpv, "sgg": sgg} if ctpv else None,
        "chunks_raw": {
            "요약": item.get("servDgst", ""),  # 상세 정보가 없어 요약만 사용
        }
    }


# --------------------------------------------------------
# 공통 전처리 — 파일 종류에 상관없이 동일하게 동작

def process_file(file_path, normalize_fn):
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    results = []
    for item in raw_data:
        normalized = normalize_fn(item)

        chunks = []
        for chunk_type, content in normalized["chunks_raw"].items():
            if content:
                text = f"[정책명: {normalized['servNm']}] {chunk_type}: {content}"
                chunks.append({"type": chunk_type, "content": text})
                texts_to_embed.append(text)

        # 지역 메타데이터 구성
        region = normalized["region"]
        if region:
            region_type = "local"
            region_code = f"{region['ctpv']}::{region['sgg']}"
            ctpv_name = region["ctpv"]
            sgg_name = region["sgg"]
        else:
            region_type = "central"
            region_code = "중앙"
            ctpv_name = ""
            sgg_name = ""

        metadata = {
            "servId": normalized["servId"],
            "servNm": normalized["servNm"],
            "servDgst": normalized["servDgst"],
            "jurMnofNm": normalized["jurMnofNm"],
            "srvPvsnNm": normalized["srvPvsnNm"],
            "lifeArray": normalized["life"],
            "intrsThemaArray": normalized["theme"],
            "trgterIndvdlArray": normalized["target"],
            "region_type": region_type,
            "region_code": region_code,
            "ctpv_name": ctpv_name,
            "sgg_name": sgg_name,
        }

        results.append({"metadata": metadata, "chunks": chunks})

    return results


texts_to_embed = []  # process_file 안에서 전역으로 채워짐

structured_data = []
structured_data += process_file('DataList1.json', normalize_list1)
structured_data += process_file('DataList2.json', normalize_list2)

print(f"전처리 완료: 총 {len(structured_data)}개 정책, {len(texts_to_embed)}개 청크")


# --------------------------------------------------------
# db 적재

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
emb_model = "solar-embedding-1-large-passage"

solar_emb = UpstageEmbeddings(
    api_key=api_key,
    model=emb_model
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

# 지역 코드 유일성 제약 — 광주 서구 / 부산 서구 같은 동명 지역 충돌 방지
graph.query("""
CREATE CONSTRAINT district_code_unique IF NOT EXISTS
FOR (d:District) REQUIRE d.code IS UNIQUE
""")

# Neo4j Cypher 쿼리문
ingestion_query = """
// 1) 정책(Policy) 본체 노드 생성
MERGE (p:Policy {servId: $metadata.servId})
SET p.servNm = $metadata.servNm,
    p.servDgst = $metadata.servDgst

// 2) 부처, 제공유형 등 메타데이터 연결
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

// 3) 지역 연결 — 중앙이면 단일 Region 노드, 지자체면 Province-District 계층
FOREACH (_ IN CASE WHEN $metadata.region_type = "central" THEN [1] ELSE [] END |
    MERGE (r:Region {code: "중앙"})
    MERGE (p)-[:AVAILABLE_IN]->(r)
)
FOREACH (_ IN CASE WHEN $metadata.region_type = "local" THEN [1] ELSE [] END |
    MERGE (prov:Province {name: $metadata.ctpv_name})
    MERGE (dist:District {code: $metadata.region_code})
      ON CREATE SET dist.name = $metadata.sgg_name
    MERGE (prov)-[:HAS_DISTRICT]->(dist)
    MERGE (p)-[:AVAILABLE_IN]->(dist)
)

// 4) 정보 조각(Chunk) 노드 생성 및 HAS_INFO 관계로 연결
FOREACH (chk IN $chunks |
    MERGE (c:Chunk {id: $metadata.servId + '_' + chk.type})
    SET c.type = chk.type,
        c.content = chk.content,
        c.embedding = chk.embedding
    MERGE (p)-[:HAS_INFO]->(c)
)
"""

print("db적재")
for i, data in enumerate(structured_data):
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

print("전체 완료")
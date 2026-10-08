import os
from dotenv import load_dotenv, find_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_upstage import ChatUpstage
from langchain_upstage.embeddings import UpstageEmbeddings



# ---------------------------------------------------------
# LLM 
load_dotenv(find_dotenv())
api_key=os.getenv('UPSTAGE_API_KEY')


#대화
chat_llm = ChatUpstage(model="solar-pro", timeout=60, max_retries=1, temperature=0)

#임베딩 모델
query_emb_model = UpstageEmbeddings(
    api_key=api_key,
    model="solar-embedding-1-large-query",
    timeout=60
)
#db연결
graph = Neo4jGraph()


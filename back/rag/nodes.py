import os
from dotenv import load_dotenv, find_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_upstage import ChatUpstage
from langchain_upstage.embeddings import UpstageEmbeddings

from state import AgentState, IntentClassification
from prompts import (
    INTENT_SYSTEM_PROMPT, 
    ANSWER_SYSTEM_PROMPT, 
    GENERAL_CHAT_PROMPT, 
    ASK_DETAILS_PROMPT,
    SUMMERIZE_SYSTEM_PROMPT
)

# ---------------------------------------------------------
# LLM 
load_dotenv(find_dotenv())
api_key=os.getenv('UPSTAGE_API_KEY')


#대화
chat_llm = ChatUpstage(model="solar-pro")

#임베딩 모델
query_emb_model = UpstageEmbeddings(
    api_key=api_key,
    model="solar-embedding-1-large-query"
)
#db연결
graph = Neo4jGraph()


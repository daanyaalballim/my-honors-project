import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
    FAISS_INDEX_PATH = os.getenv('FAISS_INDEX_PATH', 'vector_store/faiss_index')
    TOP_K_RESULTS = int(os.getenv('TOP_K_RESULTS', 3))
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database.db')
    SYSTEM_PROMPT = """You are a friendly and factual academic assistant. 
    Use the provided student guide content to answer questions accurately. 
    If you don't know the answer, say you don't know rather than making something up."""
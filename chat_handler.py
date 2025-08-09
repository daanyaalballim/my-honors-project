import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import Config
from typing import List, Dict
import openai
from constants import TONE_PRESETS, PREDEFINED_PERSONAS, LEARNING_STYLES

class ChatHandler:
    def __init__(self):
        self.embedding_model = Config.EMBEDDING_MODEL
        self.index = faiss.read_index(Config.FAISS_INDEX_PATH)
        with open(os.path.join(os.path.dirname(Config.FAISS_INDEX_PATH), 'metadata.pkl'), 'rb') as f:
            self.metadata = pickle.load(f)
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding with proper text encoding handling"""
        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
            response = openai.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * 1536 
    
    def get_relevant_chunks(self, query_embedding: List[float]) -> List[Dict]:
        """Retrieve top-k relevant chunks from vector store"""
        distances, indices = self.index.search(np.array([query_embedding]), Config.TOP_K_RESULTS)
        
        relevant_chunks = []
        for idx in indices[0]:
            if idx >= 0: 
                chunk_info = self.metadata[idx]
                relevant_chunks.append({
                    'text': chunk_info['text'],
                    'source': chunk_info['source'],
                    'page': chunk_info['page']
                })
        return relevant_chunks
    
    def get_persona_prompt(self, user_profile: Dict) -> str:
        """Generate persona-specific prompt section"""
        if user_profile.get('persona_type') == 'custom':
            return f"You adopt this persona: {user_profile.get('custom_persona', '')}"
        return PREDEFINED_PERSONAS.get(user_profile.get('persona_key', ''), '')
    
    def construct_prompt(self, user_profile: Dict, context_chunks: List[Dict], query: str) -> List[Dict]:
        """Construct the final prompt with all customizations"""
        tone = TONE_PRESETS.get(user_profile.get('tone', 'warm'), '')
        persona = self.get_persona_prompt(user_profile)
        explanation = LEARNING_STYLES.get(user_profile.get('explanation_style', 'detailed'), '')
        formatted_chunks = "\n".join(
            f"- {chunk['text']}\n  (source: {chunk['source']}, page {chunk['page']})"
            for chunk in context_chunks
        )
        
        system_prompt = f"""
        You are an educational chatbot for South African university students.
        {tone}
        {persona}
        {explanation}
        Current language preference: {user_profile.get('language', 'english')}
        
        Use this context from student guides:
        {formatted_chunks}
        """
        
        return [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": query}
        ]
    
    def get_chat_response(self, messages: List[Dict]) -> str:
        """Get response from OpenAI API"""
        response = openai.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content


chat_handler = ChatHandler()

def process_query(user_id: int, message: str, chat_id: int) -> str:
    from database import get_db_connection
    with get_db_connection() as conn:
        user_profile = conn.execute(
            "SELECT language, tone, persona_type, persona_key, custom_persona, explanation_style "
            "FROM Users WHERE user_id = ?", 
            (user_id,)
        ).fetchone()
    query_embedding = chat_handler.get_embedding(message)
    relevant_chunks = chat_handler.get_relevant_chunks(query_embedding)

    messages = chat_handler.construct_prompt(
        user_profile=dict(user_profile),
        context_chunks=relevant_chunks,
        query=message
    )
    return chat_handler.get_chat_response(messages)
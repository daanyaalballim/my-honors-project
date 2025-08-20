import os
import pickle
import numpy as np
import faiss
from config import Config
from typing import List, Dict
import openai
from constants import TONE_PRESETS, PREDEFINED_PERSONAS, LEARNING_STYLES

class ChatHandler:
    def __init__(self):
        try:
            self.embedding_model = Config.EMBEDDING_MODEL
            self.index = faiss.read_index(Config.FAISS_INDEX_PATH)
            
            metadata_path = os.path.join(
                os.path.dirname(Config.FAISS_INDEX_PATH), 
                'metadata.pkl'
            )
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
                
        except Exception as e:
            raise RuntimeError(f"Initialization failed: {str(e)}")

    def get_embedding(self, text: str) -> List[float]:
        clean_text = self._clean_text(text)
        response = openai.embeddings.create(
            input=clean_text,
            model=self.embedding_model
        )
        return response.data[0].embedding

    def _clean_text(self, text: str) -> str:
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        return text.encode('utf-8', errors='ignore').decode('utf-8')

    def get_relevant_chunks(self, query_embedding: List[float]) -> List[Dict]:
        query_array = np.array([query_embedding]).astype('float32')
        distances, indices = self.index.search(query_array, Config.TOP_K_RESULTS)
        return [
            self.metadata[idx] 
            for idx in indices[0] 
            if 0 <= idx < len(self.metadata)
        ]

    def construct_prompt(self, user_profile: Dict, context_chunks: List[Dict], query: str) -> List[Dict]:
        tone = TONE_PRESETS.get(user_profile.get('tone', 'warm'), '')
        persona = self._get_persona_prompt(user_profile)
        learning_style = LEARNING_STYLES.get(user_profile.get('explanation_style', 'detailed'), '')
        
        context_formatted = "\n".join(
            f"Excerpt from {chunk['source']}, page {chunk['page']}: {chunk['text']}"
            for chunk in context_chunks
        )
        
        system_message = (
            f"You are an academic assistant for South African students. "
            f"Respond in a {tone.lower()} manner. "
            f"{persona} "
            f"{learning_style} "
            f"Use this context: {context_formatted}"
        )
        
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": query}
        ]

    def _get_persona_prompt(self, user_profile: Dict) -> str:
        if user_profile.get('persona_type') == 'custom':
            return user_profile.get('custom_persona', '')
        return PREDEFINED_PERSONAS.get(user_profile.get('persona_key', ''), '')

    def get_chat_response(self, messages: List[Dict]) -> str:
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
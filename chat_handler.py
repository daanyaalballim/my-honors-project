import openai
import faiss
import numpy as np
from config import Config
from database import get_recent_messages
import os
import pickle

openai.api_key = Config.OPENAI_API_KEY

class ChatHandler:
    def __init__(self):
        # Load FAISS index
        self.index = faiss.read_index(Config.FAISS_INDEX_PATH)
        
        # Load metadata
        with open(os.path.join(os.path.dirname(Config.FAISS_INDEX_PATH), 'metadata.pkl'), 'rb') as f:
            self.metadata = pickle.load(f)
    
    def get_relevant_chunks(self, query_embedding):
        # Search the FAISS index
        distances, indices = self.index.search(np.array([query_embedding]), Config.TOP_K_RESULTS)
        
        # Retrieve the relevant chunks
        relevant_chunks = []
        for idx in indices[0]:
            if idx >= 0:  # FAISS may return -1 for invalid indices
                chunk_info = self.metadata[idx]
                relevant_chunks.append({
                    'text': chunk_info['text'],
                    'source': chunk_info['source'],
                    'page': chunk_info['page']
                })
        return relevant_chunks
    
    def construct_prompt(self, user_id, message, chat_id):
        # Get recent conversation history
        recent_messages = get_recent_messages(chat_id, limit=5)
        
        # Get relevant chunks from knowledge base
        query_embedding = openai.embeddings.create(
            input=message,
            model=Config.EMBEDDING_MODEL
        ).data[0].embedding
        
        relevant_chunks = self.get_relevant_chunks(query_embedding)
        
        # Construct system message with relevant chunks
        system_message = Config.SYSTEM_PROMPT + "\n\nRelevant information from student guides:\n"
        for chunk in relevant_chunks:
            system_message += f"- {chunk['text']}\n(source: {chunk['source']}, page {chunk['page']})\n\n"
        
        # Build messages list for OpenAI API
        messages = [{"role": "system", "content": system_message}]
        
        for msg in recent_messages:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def get_chat_response(self, messages):
        response = openai.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content

chat_handler = ChatHandler()

def process_query(user_id, message, chat_id):
    messages = chat_handler.construct_prompt(user_id, message, chat_id)
    response = chat_handler.get_chat_response(messages)
    return response
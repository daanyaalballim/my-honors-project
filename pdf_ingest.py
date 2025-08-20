import os
import fitz  # PyMuPDF
from config import Config
import openai
import numpy as np
import faiss
import pickle
from tqdm import tqdm
from typing import List, Dict

openai.api_key = Config.OPENAI_API_KEY

class PDFProcessor:
    def __init__(self):
        self.chunks = []
        self.metadata = []
        self.embeddings = []
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text with encoding handling"""
        text = ""
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text += page_text.encode('utf-8', errors='ignore').decode('utf-8')
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")
        return text
    
    def chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """Split text into chunks of approximately chunk_size tokens."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            current_chunk.append(word)
            current_size += 1
            if current_size >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_size = 0
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a text chunk."""
        response = openai.embeddings.create(
            input=text,
            model=Config.EMBEDDING_MODEL
        )
        return response.data[0].embedding
    
    def process_pdf(self, pdf_path: str):
        """Process a single PDF file."""
        filename = os.path.basename(pdf_path)
        text = self.extract_text_from_pdf(pdf_path)
        chunks = self.chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            embedding = self.get_embedding(chunk)
            self.chunks.append(chunk)
            self.metadata.append({
                'text': chunk,
                'source': filename,
                'page': i // 5,
                'chunk_index': i
            })
            self.embeddings.append(embedding)
    
    def save_to_faiss(self, output_path: str):
        """Save embeddings to FAISS index and metadata to pickle."""
        if not self.embeddings:
            raise ValueError("No embeddings to save")
        embeddings_array = np.array(self.embeddings).astype('float32')
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        faiss.write_index(index, output_path)
        metadata_path = os.path.join(os.path.dirname(output_path), 'metadata.pkl')
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)

def ingest_pdfs(pdf_dir: str):
    """Process all PDFs in a directory and create FAISS index."""
    processor = PDFProcessor()
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]

    for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
        pdf_path = os.path.join(pdf_dir, pdf_file)
        processor.process_pdf(pdf_path)
    processor.save_to_faiss(Config.FAISS_INDEX_PATH)
    
    print(f"Processed {len(processor.chunks)} chunks from {len(pdf_files)} PDFs")
    print(f"FAISS index saved to {Config.FAISS_INDEX_PATH}")
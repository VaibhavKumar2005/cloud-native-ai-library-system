import os
from pathlib import Path
from dotenv import load_dotenv

# Try loading from multiple possible locations
possible_paths = [
    Path(__file__).parent.parent.parent.parent / ".env",  # Workspace root (up 4 levels)
    Path.cwd() / ".env",  # Current working directory
    Path(".") / ".env",  # Relative to cwd
]

for env_path in possible_paths:
    if env_path.exists():
        print(f"✅ Loading .env from: {env_path}")
        load_dotenv(dotenv_path=env_path)
        break
else:
    print("⚠️ Warning: .env not found in any expected location. Using environment variables.")
    load_dotenv()

import faiss
import numpy as np
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_core.messages import HumanMessage
import json

class RAGService:
    def __init__(self):
        # Initialize Azure OpenAI
        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            deployment_id="text-embedding-3-large"  # or your embedding model
        )
        
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-4-nano"),
            temperature=0.7
        )
        
        # FAISS index
        self.index = None
        self.chunks = []
        self.metadata = {}
        self.index_path = "data/faiss_index"
        self.chunks_path = "data/chunks.json"
        
        # Load existing index if available
        self._load_index()
    
    def add_documents(self, chunks: list[str], source: str):
        """Add document chunks to FAISS index."""
        try:
            # Generate embeddings
            embeddings = self.embeddings.embed_documents(chunks)
            embeddings = np.array(embeddings).astype(np.float32)
            
            if self.index is None:
                # Create new index
                self.index = faiss.IndexFlatL2(embeddings.shape[1])
            
            # Add to index
            self.index.add(embeddings)
            
            # Store chunks and metadata
            for i, chunk in enumerate(chunks):
                chunk_id = len(self.chunks)
                self.chunks.append(chunk)
                self.metadata[chunk_id] = {
                    "source": source,
                    "chunk_index": len(self.chunks) - 1
                }
            
            # Save index
            self._save_index()
            
        except Exception as e:
            raise Exception(f"Error adding documents: {str(e)}")
    
    def query(self, question: str, top_k: int = 3) -> dict:
        """Query the RAG system."""
        if self.index is None:
            raise Exception("No documents loaded. Upload documents first.")
        
        try:
            # Embed question
            question_embedding = self.embeddings.embed_query(question)
            question_embedding = np.array([question_embedding]).astype(np.float32)
            
            # Search FAISS
            distances, indices = self.index.search(question_embedding, top_k)
            
            # Retrieve context
            context = [self.chunks[idx] for idx in indices[0]]
            
            # Generate answer with LLM
            context_text = "\n\n".join(context)
            prompt = f"""You are a helpful assistant. Answer the question based on the provided context.

Context:
{context_text}

Question: {question}

Answer:"""
            
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            answer = response.content
            
            # Get sources
            sources = list(set([self.metadata[idx]["source"] for idx in indices[0]]))
            
            return {
                "answer": answer,
                "context": context,
                "sources": sources
            }
        
        except Exception as e:
            raise Exception(f"Error querying: {str(e)}")
    
    def _save_index(self):
        """Save FAISS index to disk."""
        os.makedirs("data", exist_ok=True)
        if self.index:
            faiss.write_index(self.index, self.index_path)
        with open(self.chunks_path, 'w') as f:
            json.dump({
                "chunks": self.chunks,
                "metadata": {str(k): v for k, v in self.metadata.items()}
            }, f)
    
    def _load_index(self):
        """Load FAISS index from disk."""
        if os.path.exists(self.index_path) and os.path.exists(self.chunks_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.chunks_path, 'r') as f:
                    data = json.load(f)
                    self.chunks = data["chunks"]
                    self.metadata = {int(k): v for k, v in data["metadata"].items()}
            except Exception as e:
                print(f"Warning: Could not load index: {e}")

import os
import json
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import PGVector
from ai_engine.models import Document

# --- CONFIGURATION ---
# Ensure this matches your Docker/Local Postgres setup
import os
CONNECTION_STRING = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://admin:devpassword@localhost:5432/library_db"
)
COLLECTION_NAME = "rag_collection"

def get_embedding_model():
    """Helper to get the embedding model with the API key."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing! Check your .env file.")
    
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=api_key
    )

# --- 1. THE INGESTION ENGINE (Reading & Saving) ---
def ingest_document(doc_id):
    """Reads a PDF from the Document model and saves it to the Vector Database."""
    try:
        # Fetch the document path from Django
        doc = Document.objects.get(id=doc_id)
        file_path = doc.file.path
        print(f"📄 Processing: {doc.title}")

        # Load PDF
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        
        # Split text (Overlap ensures context isn't lost between chunks)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(raw_docs)
        print(f"✂️  Split into {len(chunks)} chunks.")

        # Save to Vector DB
        print("💾 Saving to Vector Database...")
        PGVector.from_documents(
            embedding=get_embedding_model(),
            documents=chunks,
            collection_name=COLLECTION_NAME, # Shared collection name
            connection_string=CONNECTION_STRING,
            pre_delete_collection=False
        )
        
        # Mark as processed in Django
        doc.processed = True
        doc.save()
        print("✅ Success! Document is now searchable.")
        return True

    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        return False

# --- 2. THE VERIFICATION ENGINE (Retrieving & Answering) ---
def get_verified_answer(query):
    """Searches the DB, generates an answer using Gemini, and verifies it."""
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return {"answer": "System Error: Missing API Key", "faithfulness_score": 0}

        # Connect to the EXISTING vector store (Read-Only mode)
        vector_db = PGVector(
            collection_name=COLLECTION_NAME, # Must match ingestion name
            connection_string=CONNECTION_STRING,
            embedding_function=get_embedding_model(),
        )

        # RETRIEVAL: Find top 3 relevant context pieces
        # This uses Cosine Similarity to find the best matches
        docs = vector_db.similarity_search(query, k=3)
        
        if not docs:
            return {
                "answer": "I couldn't find any relevant information in the uploaded documents.",
                "faithfulness_score": 0.0,
                "explanation": "No matching vectors found in the database.",
                "source_citation": "None"
            }

        context = "\n---\n".join([doc.page_content for doc in docs])

        # VERIFICATION PROMPT: The Core of Project 46
        prompt = f"""
        You are a strictly faithful AI Librarian. Use ONLY the provided context to answer the user's question.
        
        Context from PDF:
        {context}
        
        User Question: {query}
        
        Your response must be in this JSON format:
        {{
            "answer": "Your clear answer here.",
            "faithfulness_score": 0.0 to 1.0,
            "explanation": "Briefly explain why this score was given.",
            "source_citation": "Direct quote or page/paragraph reference."
        }}
        
        If the answer is NOT in the context, return score 0 and state 'Information not found'.
        """

        # Call Gemini Generative Model
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Clean the response (strip markdown formatting if Gemini adds it)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        
        return json.loads(clean_json)

    except Exception as e:
        return {
            "answer": "I encountered an error while processing your request.",
            "faithfulness_score": 0,
            "explanation": str(e),
            "source_citation": "System Error"
        }
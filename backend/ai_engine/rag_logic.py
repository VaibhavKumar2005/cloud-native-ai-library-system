import os
import json
import logging
import hvac  # For HashiCorp Vault
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import PGVector
from ai_engine.models import Document

# Set up logging for debugging
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DB_USER = os.environ.get("POSTGRES_USER", "admin")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "devpassword")
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres") 
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "library_db")

# Construct the connection string using the 'postgres' hostname
CONNECTION_STRING = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
COLLECTION_NAME = "rag_collection"

# --- VAULT INTEGRATION ---
def get_api_key_from_vault():
    """Connects to Vault and securely retrieves the Google API Key from memory."""
    try:
        client = hvac.Client(
            url='http://vault:8200',
            token=os.environ.get('VAULT_TOKEN')
        )
        # Read from KV v2 secret engine path established earlier
        secret_response = client.secrets.kv.v2.read_secret_version(path='myapp')
        return secret_response['data']['data']['GOOGLE_API_KEY']
    except Exception as e:
        logger.error(f"Vault Security Error: {str(e)}")
        return None

def get_embedding_model():
    """Helper to get the embedding model using the secure API key."""
    api_key = get_api_key_from_vault()
    if not api_key:
        raise ValueError("Vault Error: GOOGLE_API_KEY is missing or Vault is sealed!")
    
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=api_key
    )

# --- 1. THE INGESTION ENGINE (Multi-Tenant Updated) ---
def ingest_document(doc_id):
    """Reads a PDF, tags it with the owner's ID, and saves to Vector DB."""
    try:
        doc = Document.objects.get(id=doc_id)
        file_path = doc.file.path
        logger.info(f"📄 Processing: {doc.title}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        # Load and Split
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(raw_docs)
        
        # 🚨 METADATA INJECTION: Tag chunks with the user's ID
        for chunk in chunks:
            # We use str() just in case the UUID/ID format causes issues with PGVector
            chunk.metadata["user_id"] = str(doc.user.id) if doc.user else "public"
        
        # Save to Vector DB
        PGVector.from_documents(
            embedding=get_embedding_model(),
            documents=chunks,
            collection_name=COLLECTION_NAME,
            connection_string=CONNECTION_STRING,
            pre_delete_collection=False
        )
        
        doc.processed = True
        doc.save()
        logger.info("✅ Document indexed successfully.")
        return True

    except Exception as e:
        logger.error(f"❌ Ingestion failed: {str(e)}")
        return False

# --- 2. THE VERIFICATION ENGINE (Multi-Tenant Updated) ---
def get_verified_answer(query, user_id):
    """Retrieves context specific to the user and generates a verified response."""
    try:
        # Secure fetch from Vault
        api_key = get_api_key_from_vault()
        if not api_key:
            return {"answer": "System Error: Missing API Key from Vault", "faithfulness_score": 0}

        # 1. RETRIEVAL WITH ISOLATION
        vector_db = PGVector(
            collection_name=COLLECTION_NAME,
            connection_string=CONNECTION_STRING,
            embedding_function=get_embedding_model(),
        )
        
        # 🚨 TENANT FILTER: Only search vectors belonging to this specific user
        docs = vector_db.similarity_search(
            query, 
            k=3,
            filter={"user_id": str(user_id)} 
        )
        
        if not docs:
            return {
                "answer": "I couldn't find any relevant information in your uploaded documents.",
                "faithfulness_score": 0.0,
                "explanation": "No matching vectors found for this user in the database.",
                "source_citation": "None"
            }

        context = "\n\n".join([f"[Source: Page {d.metadata.get('page', 'Unknown')}] {d.page_content}" for d in docs])

        # 2. GENERATION WITH JSON MODE
        genai.configure(api_key=api_key)
        
        generation_config = {
            "temperature": 0.0,
            "response_mime_type": "application/json"
        }
        
        model = genai.GenerativeModel('gemini-1.5-flash', generation_config=generation_config)

        prompt = f"""
        You are VeriRag, a strictly faithful AI Librarian.
        Analyze the following context and answer the user's question.
        
        CONTEXT:
        {context}
        
        QUESTION: 
        {query}
        
        INSTRUCTIONS:
        1. Answer ONLY using the provided context.
        2. If the answer is not in the context, return score 0.
        3. You must provide a "faithfulness_score" between 0.0 and 1.0 (1.0 = perfect evidence).
        4. "source_citation" must be a direct quote from the text.
        
        Output valid JSON with this schema:
        {{
            "answer": "string",
            "faithfulness_score": float,
            "explanation": "string",
            "source_citation": "string"
        }}
        """

        response = model.generate_content(prompt)
        
        # 3. PARSE
        return json.loads(response.text)

    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        return {
            "answer": "I encountered an error while processing your request.",
            "faithfulness_score": 0,
            "explanation": f"Internal Error: {str(e)}",
            "source_citation": "System Error"
        }
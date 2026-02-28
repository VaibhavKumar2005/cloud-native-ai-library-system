import os
import json
import logging
import hvac  # For HashiCorp Vault
import google.generativeai as genai
from openai import OpenAI  # Used for the Groq Fallback
from prometheus_client import Counter # <--- ADDED FOR MONITORING
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import PGVector
from ai_engine.models import Document

# Set up logging for debugging
logger = logging.getLogger(__name__)

# --- CUSTOM METRICS FOR MISSION CONTROL ---
# These must match the names used in your SystemInsightsView
VERIFICATION_REJECTIONS = Counter(
    'verirag_hallucination_rejections_total',
    'Total number of AI responses rejected for low faithfulness'
)

LLM_FALLBACKS = Counter(
    'verirag_llm_fallbacks_total',
    'Total number of times the system switched to the backup LLM'
)

# --- CONFIGURATION ---
DB_USER = os.environ.get("POSTGRES_USER", "admin")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "devpassword")
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres") 
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "library_db")

CONNECTION_STRING = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
COLLECTION_NAME = "rag_collection"

# --- VAULT INTEGRATION ---
def get_api_key_from_vault():
    try:
        client = hvac.Client(
            url='http://vault:8200',
            token=os.environ.get('VAULT_TOKEN')
        )
        secret_response = client.secrets.kv.v2.read_secret_version(path='myapp')
        return secret_response['data']['data']['GOOGLE_API_KEY']
    except Exception as e:
        logger.error(f"Vault Security Error: {str(e)}")
        return None

def get_embedding_model():
    api_key = get_api_key_from_vault()
    if not api_key:
        raise ValueError("Vault Error: GOOGLE_API_KEY is missing or Vault is sealed!")
    
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=api_key
    )

# --- 1. THE INGESTION ENGINE ---
def ingest_document(doc_id):
    try:
        doc = Document.objects.get(id=doc_id)
        file_path = doc.file.path
        logger.info(f"📄 Processing: {doc.title}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(raw_docs)
        
        for chunk in chunks:
            chunk.metadata["user_id"] = str(doc.user.id) if doc.user else "public"
        
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

# --- FALLBACK ROUTER ---
def call_llm_with_fallback(prompt, api_key):
    """Tries Gemini first, falls back to Groq (Llama 3) if it fails."""
    try:
        genai.configure(api_key=api_key)
        generation_config = {
            "temperature": 0.0,
            "response_mime_type": "application/json"
        }
        model = genai.GenerativeModel('gemini-1.5-flash', generation_config=generation_config)
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as primary_error:
        # 🚨 LOG METRIC: Gemini Failed
        LLM_FALLBACKS.inc() 
        logger.warning(f"Gemini failed: {primary_error}. Switching to Backup Model (Groq)...")
        
        try:
            backup_client = OpenAI(
                api_key=os.environ.get("GROQ_API_KEY", "missing_key"),
                base_url="https://api.groq.com/openai/v1" 
            ) 
            response = backup_client.chat.completions.create(
                model="llama3-8b-8192", 
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Always output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }, 
                temperature=0.0
            )
            return response.choices[0].message.content
            
        except Exception as backup_error:
            logger.error(f"Backup model also failed: {backup_error}")
            return json.dumps({
                "answer": "System Notice: All AI providers are down.",
                "faithfulness_score": 0.0,
                "explanation": "Failover triggered but backup also failed.",
                "source_citation": "System Error"
            })

# --- 2. THE VERIFICATION ENGINE ---
def get_verified_answer(query, user_id):
    try:
        api_key = get_api_key_from_vault()
        if not api_key:
            return {"answer": "System Error: Missing API Key from Vault", "faithfulness_score": 0}

        vector_db = PGVector(
            collection_name=COLLECTION_NAME,
            connection_string=CONNECTION_STRING,
            embedding_function=get_embedding_model(),
        )
        
        docs = vector_db.similarity_search(
            query, 
            k=3,
            filter={"user_id": str(user_id)} 
        )
        
        if not docs:
            return {
                "answer": "I couldn't find any relevant information in your uploaded documents.",
                "faithfulness_score": 0.0,
                "explanation": "No matching vectors found for this user.",
                "source_citation": "None"
            }

        context = "\n\n".join([f"[Source: Page {d.metadata.get('page', 'Unknown')}] {d.page_content}" for d in docs])

        prompt = f"""
        You are VeriRag, a strictly faithful AI Librarian.
        ... (prompt instructions) ...
        Output valid JSON:
        {{
            "answer": "string",
            "faithfulness_score": 0.0,
            "explanation": "string",
            "source_citation": "string"
        }}
        """

        response_text = call_llm_with_fallback(prompt, api_key)
        response_data = json.loads(response_text)

        # 🚨 LOG METRIC: Track Low Faithfulness (Potential Hallucination)
        if response_data.get("faithfulness_score", 0) < 0.6:
            VERIFICATION_REJECTIONS.inc()

        return response_data

    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        return {
            "answer": "Internal Error",
            "faithfulness_score": 0,
            "explanation": str(e),
            "source_citation": "System Error"
        }
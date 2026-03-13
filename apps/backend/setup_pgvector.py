"""
Script to set up pgvector extension in PostgreSQL
Run this once before using the RAG system
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Database connection parameters
DB_CONFIG = {
    'dbname': os.environ.get('POSTGRES_DB', 'library_db'),
    'user': os.environ.get('POSTGRES_USER', 'admin'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'devpassword'),
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': '5432'
}

def setup_pgvector():
    """Enable pgvector extension in the database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("🔌 Connected to PostgreSQL")
        
        # Create extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("✅ pgvector extension enabled")
        
        # Verify
        cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()
        if result:
            print(f"✅ Verified: pgvector {result[1]} is installed")
        
        cursor.close()
        conn.close()
        print("✅ Setup complete! Your RAG system is ready.")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        print("\n💡 Make sure:")
        print("   1. PostgreSQL is running")
        print("   2. The database 'library_db' exists")
        print("   3. pgvector is installed (download from https://github.com/pgvector/pgvector)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Setting up pgvector for VeriRAG...")
    setup_pgvector()

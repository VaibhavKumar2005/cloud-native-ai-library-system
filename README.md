# 📚 Librarian: Verifiable Cloud-Native RAG System
> **Academic Project 46:** Retrieval-Augmented Generation for Verifiable and Faithful Text Generation.

## 🚀 Overview
**Librarian** is an advanced **Verifiable RAG (Retrieval-Augmented Generation) System** designed to solve the critical problem of LLM hallucinations in high-stakes environments. 

Unlike standard chatbots that simply "guess" answers based on retrieved text, Librarian implements a **Closed-Loop Verification Architecture**. It introduces a secondary "Critic" agent that mathematically evaluates the faithfulness of every generated answer against the source documents before presenting it to the user.

## 🏗 Architecture
The system moves beyond linear RAG pipelines to a cyclic **Generate-Verify-Refine** workflow:

1.  **Ingestion Layer:** - PDFs are parsed, chunked, and embedded using **Google Gemini** embeddings.
    - Vectors are stored in **PostgreSQL** using the `pgvector` extension for high-dimensional semantic search.
2.  **Retrieval Engine (`librarian` app):** - Performs semantic search to retrieve the top-k most relevant document chunks.
3.  **Generation:** - The LLM drafts a response citing specific chunk IDs (e.g., `[Source: 12]`).
4.  **The Verifier (`verifier` app) — *Core Innovation*:** - A dedicated "Critic" module cross-references the drafted answer against the raw source text.
    - Calculates a **Faithfulness Score** (0-100%).
    - If the score is low, the system flags the answer as a hallucination or attempts a regeneration.

## ⚡ Key Features (Project Requirements)
- [x] **Answer-Evidence Alignment:** Automated verification ensuring every claim is backed by source text.
- [x] **Faithfulness Scoring:** Real-time reliability metric displayed to the user (e.g., 🟢 95% Verified).
- [x] **Granular Citations:** Clickable references linking directly to the specific PDF page and paragraph.
- [x] **Hallucination Detection:** proactively filters out unsupported claims.
- [x] **Cloud-Native Deployment:** Containerized microservices architecture ready for Azure Kubernetes Service (AKS).

## 🛠 Tech Stack

### **Backend & AI**
* **Framework:** Django & Django REST Framework (Python)
* **Database:** PostgreSQL + `pgvector` (Vector Database)
* **LLM Engine:** LangChain + Google Gemini Pro (via API)
* **Task Queue:** Celery (for asynchronous document processing)

### **Frontend**
* **Library:** React.js
* **Styling:** Tailwind CSS
* **Visualization:** Faithfulness score indicators and PDF highlighting.

### **Infrastructure (DevOps)**
* **Containerization:** Docker & Docker Compose
* **Cloud Provider:** Microsoft Azure
* **Registry:** Azure Container Registry (ACR)
* **Orchestration:** Ready for Kubernetes (AKS)

---

## 🔧 Setup & Installation

### **1. Prerequisites**
* Python 3.10+
* Node.js (v18+)
* PostgreSQL (with `vector` extension)
* Azure CLI
* Google Gemini API Key

### **2. Backend Setup (Django)**
```bash
# Clone the repository
git clone [https://github.com/yourusername/librarian-rag.git](https://github.com/yourusername/librarian-rag.git)
cd librarian-rag

# Activate Virtual Environment
# Windows
.\venv\Scripts\Activate.ps1
# Linux/Mac
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt

# Configure Environment Variables
# Create a .env file in the root directory:
# GOOGLE_API_KEY=your_gemini_key
# DATABASE_URL=postgres://user:password@localhost:5432/librarian_db
# DEBUG=True

# Database Migrations
python manage.py makemigrations
python manage.py migrate

# Start the Development Server
python manage.py runserver
   
# VeriRAG: Enterprise-Grade Cloud-Native RAG System

Here is a simple, clear, and impressive explanation of your project to use during the 3 PM academic showcase.

## 1. What is VeriRAG? (The Elevator Pitch)
VeriRAG is a **Cloud-Native Retrieval-Augmented Generation (RAG) system** that solves one of the biggest problems with AI today: **Hallucinations**. 

Standard RAG just retrieves documents and feeds them to an LLM. VeriRAG uses a **Dual-Agent Verification System**. The *Primary Agent* (Google Gemini 2.0 Flash) generates the answer, and before the user sees it, a mathematical **Faithfulness Verification** step checks if the answer actually matches the context. If it fails, our *Fallback Agent* (Groq Llama-3.3) takes over.

## 2. Core Architecture & Workflow
When you explain how it works, walk them through this flow:

### Step 1: Ingestion & Vectorization
1. User uploads a PDF.
2. The backend extracts text, splits it into small "chunks".
3. We use **Google Gemini Embedding 001** to turn text into vector embeddings.
4. These are saved in **PostgreSQL with the `pgvector` extension** for lightning-fast similarity search.

### Step 2: The Dual-Agent RAG Query
1. A user asks a question (e.g., "What does the document say about CI/CD?").
2. The system does a **Similarity Search** in `pgvector` to find the most relevant chunks.
3. The context + question goes to **Google Gemini** (Primary LLM).
4. **The Verification Step**: We calculate a `faithfulness_score`. If the answer hallucinated information not in the text, the score drops below `0.6`.
5. **The Fallback**: If the score is low, we automatically redirect the query to **Groq's Llama-3.3-70b**.

### Step 3: Analytics & Monitoring
All metrics—faithfulness scores, hallucination rejections, fallback triggers, and total documents—are exported via **Prometheus**. The React Dashboard shows these in real-time.

## 3. DevOps & Cloud-Native Features
Your evaluators will love these specific DevOps buzzwords. Mention these explicitly:

* **CI/CD Pipeline**: We use GitHub Actions. On every push to `main`, it runs Django tests, builds Docker Images for Backend & Frontend, pushes them to **Docker Hub**, and auto-deploys to Azure.
* **Dual-Mode Secret Management**: We don't hardcode API keys! Locally we use **HashiCorp Vault**, and in Production, it seamlessly switches to **Azure Key Vault**.
* **Containerized Microservices**: The app is split into a Django API, a React Vite frontend, a PostgreSQL (`pgvector`) DB, and a Redis Cache.
* **Serverless Hosting via Azure Container Apps (ACA)**: We are deploying on Azure Container Apps, which handles auto-scaling via KEDA (Kubernetes Event-Driven Autoscaling).

## 4. How to run the Demo at 3 PM
1. Run `./deploy_demo.ps1` in PowerShell. Ensure `GOOGLE_API_KEY` and `GROQ_API_KEY` are exported in your PowerShell first!
2. The script will output the **Frontend URL** and **Backend URL**.
3. Open the Frontend, show the UI (Dashboard, Analytics).
4. Upload a document and ask a query.
5. Emphasize the "System Insights" / Metrics page to show we actually track AI hallucinations.
6. Once the demo is complete, run: `az group delete --name rg-verirag-demo --yes --no-wait` to save student credits.
# ☁️ Azure Cloud-Native RAG

A production-grade **Microservices architecture** for secure Retrieval-Augmented Generation, built with **Django**, **React**, **Docker**, and **PostgreSQL**.

This project implements a secure, scalable AI pipeline designed to run on **Azure Kubernetes Service (AKS)**. It demonstrates industry standards for container orchestration, secure backend design, and full-stack integration.

## 🏗️ System Architecture

The application is composed of Dockerized services working in harmony:

| Service | Technology | Role | Port |
| :--- | :--- | :--- | :--- |
| **Frontend** | React + Vite + Tailwind | Operational Dashboard & Control Plane | `5173` |
| **Backend** | **Python (Django + Ninja/DRF)** | API Gateway, RAG Orchestrator & Admin Panel | `8000` |
| **Vector DB** | **pgvector (PostgreSQL)** | Vector Embeddings & Relational Data | `5432` |
| **Security** | HashiCorp Vault | Secret Management & Encryption | `8200` |

## 🚀 Key Features
* **Cloud-Native:** Fully containerized and ready for Kubernetes (AKS).
* **Enterprise Backend:** powered by **Django** for robust Admin management and ORM.
* **Vector Search:** Native integration with PostgreSQL for high-performance RAG.
* **Secure DevOps:** Branch protection, CI/CD pipelines, and secrets management.

## 🛠️ Getting Started

### Prerequisites
* Docker Desktop (Running)
* Git
* Python 3.10+

### Installation & Run

1. **Clone the Repository**
   ```bash
   git clone [https://github.com/VaibhavKumar2005/azure-cloud-native-rag.git](https://github.com/VaibhavKumar2005/azure-cloud-native-rag.git)
   cd azure-cloud-native-rag
   
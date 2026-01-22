# ☁️ Azure Cloud-Native RAG

> A production-grade Microservices architecture for secure Retrieval-Augmented Generation, built with Docker, React, Flask, and HashiCorp Vault.

This project implements a secure, scalable AI pipeline designed to run on **Azure Kubernetes Service (AKS)**. It demonstrates industry standards for container orchestration, secret management, and full-stack integration.

---

## 🏗️ System Architecture

The application is composed of **5 Dockerized Microservices** working in harmony:

| Service | Technology | Role | Port |
| :--- | :--- | :--- | :--- |
| **Frontend** | React + Vite + Tailwind | Operational Dashboard & Control Plane | `5173` |
| **Backend** | Python (Flask) | API Gateway & RAG Orchestrator | `5000` |
| **Logs DB** | MongoDB | Unstructured Log Storage (NoSQL) | `27017` |
| **User DB** | PostgreSQL | Structured User Data (Relational) | `5432` |
| **Security** | HashiCorp Vault | Secret Management & Encryption | `8200` |

---

## 🚀 Getting Started

You can spin up the entire infrastructure with a single command.

### Prerequisites
* Docker Desktop (Running)
* Node.js & npm
* Git

### Installation & Run

1. **Clone the Repository**
   ```bash
   git clone [https://github.com/VaibhavKumar2005/azure-cloud-native-rag.git](https://github.com/VaibhavKumar2005/azure-cloud-native-rag.git)
   cd azure-cloud-native-rag
   
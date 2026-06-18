# 🚀 Enterprise LLM Platform

A production-grade, enterprise-ready LLM platform built using **FastAPI**, following **Clean Architecture**, **SOLID Principles**, and **LLMOps best practices**.

The platform is designed to support multiple LLM providers, Retrieval-Augmented Generation (RAG), AI Agents, hybrid search, observability, caching, and Kubernetes deployment while maintaining a clean, modular, and scalable architecture.

---

# Architecture

```
                    +----------------+
                    |     Client     |
                    +----------------+
                            |
                            ▼
                    +----------------+
                    |    FastAPI     |
                    +----------------+
                            |
                            ▼
                    +----------------+
                    | API Routers    |
                    +----------------+
                            |
                            ▼
                    +----------------+
                    | Chat Service   |
                    +----------------+
                            |
              +-------------+--------------+
              |                            |
              ▼                            ▼
      +----------------+         +----------------+
      | Retrieval      |         | Prompt Builder |
      +----------------+         +----------------+
              |                            |
              +-------------+--------------+
                            |
                            ▼
                    +----------------+
                    | LLM Service    |
                    +----------------+
                            |
            +---------------+----------------+
            |               |                |
            ▼               ▼                ▼
      Cache Policy     Retry Policy    Metrics
                            |
                            ▼
                    +----------------+
                    | LLM Provider   |
                    +----------------+
                            |
                            ▼
                    +----------------+
                    | LLM Client     |
                    +----------------+
                            |
                            ▼
                      OpenAI / Gemini /
                      Anthropic / Ollama
```

---

# Features

## Backend

- FastAPI
- Dependency Injection
- Layered Architecture
- SOLID Principles
- Pydantic Validation
- Configuration Management
- Health & Readiness APIs

---

## LLM

- OpenAI
- Gemini
- Anthropic
- Ollama
- Azure OpenAI (Planned)

---

## Retrieval

- Qdrant
- Hybrid Search
- Semantic Search
- Metadata Filtering
- Reranking

---

## AI

- Prompt Templates
- Context Window Management
- Output Parsing
- Tool Calling
- AI Agents

---

## Performance

- Redis Cache
- Retry Policy
- Circuit Breaker
- Request Timeout
- Streaming Responses

---

## Observability

- Structured Logging
- Request IDs
- Metrics
- Prometheus
- Grafana

---

## Deployment

- Docker
- Docker Compose
- Kubernetes
- Helm Charts
- GitHub Actions CI/CD

---

# Project Structure

```
enterprise-llm-platform/

├── app/
│
├── api/
│     chat.py
│     health.py
│     documents.py
│
├── services/
│     chat_service.py
│     llm_service.py
│
├── providers/
│     llm_provider.py
│     openai_provider.py
│     gemini_provider.py
│
├── clients/
│     openai_client.py
│     gemini_client.py
│
├── retrieval/
│     retriever.py
│     reranker.py
│     hybrid_search.py
│
├── prompt/
│     prompt_builder.py
│
├── parser/
│     output_parser.py
│
├── policies/
│     retry.py
│     timeout.py
│     cache.py
│     circuit_breaker.py
│
├── observability/
│     logger.py
│     metrics.py
│
├── middleware/
│     request_id.py
│
├── security/
│     authentication.py
│     guardrails.py
│
├── models/
│
├── core/
│     config.py
│     exceptions.py
│
├── dependencies.py
├── main.py
│
├── tests/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

# Request Flow

```
User

↓

Authentication

↓

Guardrails

↓

Request Validation

↓

Intent Detection

↓

Chat Service

↓

Retriever (Optional)

↓

Prompt Builder

↓

LLM Service

↓

Cache

↓

Retry

↓

Timeout

↓

Metrics

↓

Provider

↓

LLM Client

↓

LLM API

↓

Output Parser

↓

Response
```

---

# Technology Stack

| Layer | Technology |
|---------|------------|
| Language | Python 3.12 |
| API | FastAPI |
| Validation | Pydantic |
| LLM | OpenAI, Gemini |
| Vector DB | Qdrant |
| Cache | Redis |
| Database | PostgreSQL |
| Containers | Docker |
| Orchestration | Kubernetes |
| Monitoring | Prometheus |
| Dashboards | Grafana |

---

# SOLID Principles

This project follows all SOLID principles.

## Single Responsibility Principle

Each module has only one responsibility.

Example:

- Chat Service
- LLM Service
- Retriever
- Prompt Builder
- Output Parser

---

## Open Closed Principle

Adding a new LLM provider requires only:

```
providers/
```

No existing code modification.

---

## Liskov Substitution

Every provider implements

```
LLMProvider
```

allowing providers to be replaced transparently.

---

## Interface Segregation

Clients depend only on interfaces they use.

---

## Dependency Inversion

Business logic depends on abstractions rather than SDK implementations.

---

# Configuration

```
LLM_PROVIDER=gemini

MODEL_NAME=gemini-2.5-flash

TEMPERATURE=0.2

OPENAI_API_KEY=

GEMINI_API_KEY=

REDIS_URL=

QDRANT_URL=
```

---

# Running

Create Virtual Environment

```
python -m venv .venv
```

Linux

```
source .venv/bin/activate
```

Install

```
pip install -r requirements.txt
```

Run

```
uvicorn app.main:app --reload
```

Swagger

```
http://localhost:8000/docs
```

---

# Health API

```
GET /health
```

---

# Readiness API

```
GET /ready
```

---

# Chat API

```
POST /api/v1/chat
```

Request

```json
{
    "question":"What is Kubernetes?"
}
```

---

# Future Roadmap

- Redis Integration
- Qdrant Integration
- Embeddings
- Hybrid Search
- Reranking
- Prompt Engineering
- AI Agents
- Streaming
- Tool Calling
- Kubernetes Deployment
- Helm Charts
- Prometheus Metrics
- Grafana Dashboards
- GitHub Actions
- Unit Testing
- Integration Testing
- Load Testing

---

# Design Principles

- Clean Architecture
- Layered Architecture
- Dependency Injection
- Provider Abstraction
- Enterprise Scalability
- Production Observability
- Failure Isolation
- Loose Coupling
- High Cohesion

---

# Author

Murali Krishna Reddy

Built as part of an end-to-end journey toward becoming a Production LLMOps Engineer, focusing on enterprise architecture, scalable AI systems, and production-ready backend engineering.
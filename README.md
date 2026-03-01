
<p align="center">
  <img src="assets/logo.jpg" alt="Deep Nexus Logo" width="200" />
</p>

<h1 align="center">Deep Nexus</h1>

<p align="center">
  사내 정형(RDB) · 비정형(보고서, 규정 등) 데이터를 통합 검색하는 AI 기반 사내 챗봇
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white" />
</p>

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [주요 기능](#2-주요-기능)
3. [ETL 파이프라인 및 시스템 아키텍처](#3-etl-파이프라인-및-시스템-아키텍처)
4. [LangGraph 워크플로우](#4-langgraph-워크플로우)
5. [기술 스택](#5-기술-스택)
6. [프로젝트 구조](#6-프로젝트-구조)
7. [API 엔드포인트](#7-api-엔드포인트)
8. [보안](#8-보안)
9. [인프라 및 배포](#9-인프라-및-배포)
10. [환경 설정 및 실행 방법](#10-환경-설정-및-실행-방법)
11. [결과 화면 및 성과](#11-결과-및-성과)

---

## 1. 프로젝트 개요

**Deep Nexus**는 사내에 흩어져 있는 다양한 정형 데이터(RDB)와 비정형 데이터(보고서, 기획서, 사내 규정 등)를 하나의 인터페이스에서 자연어로 질의하고 통합된 답변을 받을 수 있는 **Advanced RAG(Retrieval-Augmented Generation) 기반 AI 챗봇**입니다.

직원이 "인사팀 대리급 올해 예상 연봉 총합 알려줘"처럼 자연어로 질문하면, 시스템이 자동으로 의도를 분석하여 정형 데이터(SQL 생성 및 실행)와 비정형 데이터(벡터 검색)를 조합해 하나의 답변으로 제공합니다.

### 핵심 가치

| 기존 방식 | Deep Nexus |
|---|---|
| 데이터 조회를 위해 DBA에게 요청 | 자연어 질문으로 즉시 조회 |
| 사내 규정을 찾기 위해 여러 문서 탐색 | 질문 한 번으로 관련 규정 검색 |
| 정형/비정형 데이터를 별도로 확인 | 하나의 질문으로 통합 답변 제공 |
| 접근 권한 관리가 복잡 | RLS 기반 자동 권한 제어 |

### 프로젝트는 8일간 진행되었으며, 총 6명의 팀원이 아래와 같이 역할을 담당하였습니다.

| 이름 | 담당 역할 |
|---|---|
| 배재현(본인) | **RAG 구축, 서비스 기획, Backend 리드, Reranking 도입** |
| 이*현 | UI/UX 기획, 발표 PPT 작업 |
| 김*훈 | 프로젝트 매니저, 시장 조사 |
| 이*엽 | PostgreSQL RLS 정책 적용 |
| 최*혜 | 구글 드라이드 연동 및 비정형 문서 청킹 |
| 이*은 | 프론트엔드 개발 |

---

## 2. 주요 기능

- [목차로 돌아가기](#목차)
  
- **AI 채팅** — 자연어 질문 → 의도 분석 → 정형/비정형 데이터 통합 조회 → 스트리밍 답변
- **Text-to-SQL** — 자연어를 PostgreSQL 쿼리로 변환하여 RDB 데이터 조회 (CoT 기반, 최대 3회 재시도)
- **하이브리드 벡터 검색** — HNSW 벡터 검색 + GIN 키워드 검색
- **Reranking** — 고품질의 답변을 위한 결과 청크 ONNX Reranking
- **시맨틱 캐시** — Redis Vector Search 기반 유사 질문 캐싱 (24시간 TTL)
- **파일 업로드 분석** — PDF, DOCX 등 업로드 파일 파싱 및 분석
- **음성 인식(STT)** — Faster-Whisper 기반 한국어 음성 → 텍스트 변환
- **공지사항** — 부서별 공지 CRUD
- **메일** — SMTP 기반 사내 메일 전송 및 관리
- **회의실 예약** — 월별/일별 예약 현황 조회 및 예약 관리
- **PostgreSQL RLS(Row Level Security)** — 직급/부서 기반 데이터 접근 제어

---

## 3. ETL 파이프라인 및 시스템 아키텍처

- [목차로 돌아가기](#목차)
  
### ETL 파이프라인

<p align="center">
  <img src="assets/data-pipeline.PNG" alt="Data Pipeline"/>
</p>

### 시스템 아키텍처

<p align="center">
  <img src="assets/architecture.PNG" alt="System Architecture" />
</p>

---

## 4. LangGraph 워크플로우

- [목차로 돌아가기](#목차)
  
### 워크플로우 다이어그램

```mermaid
graph TD
    START(["🚀 START"]) --> cache{"시맨틱 캐시 확인"}
    
    cache -->|Cache Hit| response["캐시된 응답 반환"]
    cache -->|Cache Miss| router

    router["🔀 Router Node<br/>질문 의도 분석 및 경로 결정"]

    router -->|"intent = rdb"| sql_agent["🗄️ SQL Agent Node<br/>Text-to-SQL 생성 및 실행"]
    router -->|"intent = vector"| vector_search["🔍 Vector Search Node<br/>하이브리드 벡터 검색"]
    router -->|"intent = both"| parallel["⚡ 병렬 실행"]
    router -->|"intent = other"| generator

    parallel --> sql_agent
    parallel --> vector_search

    sql_agent --> generator["💬 Generator Node<br/>최종 답변 생성 (Streaming)"]
    vector_search --> generator

    generator --> save["Background Task<br/>캐시 저장 & 대화 기록 저장"]
    save --> END(["🏁 END"])

    style router fill:#000000,stroke:#0288d1
    style sql_agent fill:#000000,stroke:#f57c00
    style vector_search fill:#000000,stroke:#f57c00
    style generator fill:#000000,stroke:#388e3c
    style cache fill:#000000,stroke:#7b1fa2
    style parallel fill:#000000,stroke:#c62828
```

### 단계별 설명

<p align="center">
  <img src="assets/workflow.PNG" alt="Workflow"/>
</p>

#### 1단계: 시맨틱 캐시 확인

사용자 질문이 들어오면 **Redis Vector Search**를 통해 이전에 유사한 질문이 캐싱되어 있는지 확인합니다. 코사인 거리 기준 0.1(약 90% 유사도) 이하일 경우 캐시 히트로 판정하여 즉시 응답합니다.

#### 2단계: Router Node — 의도 분석 및 경로 결정

캐시 미스 시 **GPT-4o-mini**가 질문을 분석하여 4가지 경로 중 하나를 결정합니다.

| Intent | 설명 | 실행 노드 |
|--------|------|-----------|
| `rdb` | 정형 데이터(수치, 통계, 명단) 조회 필요 | SQL Agent |
| `vector` | 비정형 문서(규정, 가이드라인) 검색 필요 | Vector Search |
| `both` | 정형 + 비정형 데이터 모두 필요한 복합 질문 | SQL Agent + Vector Search (병렬) |
| `other` | 업로드 파일 분석 또는 일반 대화 | Generator (직행) |

Router는 동시에 `sql_keywords`(Text-to-SQL용 키워드)와 `vector_query`(유의어가 포함된 확장 검색어)를 생성합니다.

#### 3단계: SQL Agent Node — 정형 데이터 처리

1. Router가 생성한 키워드로 **관련 테이블 DDL을 벡터 검색**하여 추출
2. DDL + 사용자 질문을 기반으로 **GPT-4o**가 Chain-of-Thought 방식으로 PostgreSQL 쿼리 생성
3. **Row Level Security(RLS)** 세션 변수를 주입한 후 쿼리 실행
4. 실행 실패 시 에러 메시지를 피드백하여 **최대 3회 재시도**

#### 4단계: Vector Search Node — 비정형 데이터 처리

1. Router가 생성한 확장 쿼리로 **HNSW 벡터 검색** 수행 (상위 15개)
2. 키워드 기반 **GIN 인덱스 검색**으로 추가 문서 확보
3. 두 결과를 병합 및 중복 제거 후 **ONNX Reranker**로 최종 상위 3개 문서 선정

#### 5단계: Generator Node — 최종 답변 생성

정형 데이터(RDB 결과), 비정형 데이터(문서 검색 결과), 업로드 파일, 이전 대화 기록을 모두 종합하여 최종 답변을 **토큰 단위 스트리밍**으로 생성합니다. 컨텍스트 길이에 따라 GPT-4o(15,000자 초과) 또는 GPT-4o-mini를 자동 선택합니다.

---

## 5. 기술 스택

- [목차로 돌아가기](#목차)
  
### Backend

| 분류 | 기술 | 설명 |
|------|------|------|
| **Web Framework** | FastAPI + Uvicorn | 비동기 ASGI 기반 REST API |
| **AI Orchestration** | LangGraph | 노드 기반 AI 에이전트 워크플로우 |
| **LLM** | Azure OpenAI (GPT-4o, GPT-4o-mini) | 질문 분석, SQL 생성, 답변 생성 |
| **Embedding** | KURE-v1 (HuggingFace) | 1024차원 한국어 임베딩 |
| **Reranking** | BGE-Reranker (ONNX INT8) | 문서 재순위화 |
| **STT** | Faster-Whisper | 한국어 음성 인식 |

### Data & Storage

| 분류 | 기술 | 설명 |
|------|------|------|
| **RDB** | PostgreSQL + asyncpg | 비동기 PostgreSQL 드라이버 |
| **Vector Store** | pgvector (HNSW) | PostgreSQL 벡터 확장 |
| **Keyword Search** | pg_trgm (GIN Index) | 트라이그램 기반 키워드 검색 |
| **Cache** | Redis + Redis Vector Search | 시맨틱 캐시 및 대화 메모리 |
| **ORM** | SQLAlchemy 2.0 (Async) | 비동기 ORM |

### Infra & DevOps

| 분류 | 기술 | 설명 |
|------|------|------|
| **Cloud** | Microsoft Azure | 클라우드 인프라 |
| **Container** | Azure Container Apps | 서버리스 컨테이너 배포 |
| **Monitoring** | LangSmith | LLM 트레이싱 및 모니터링 |

### 기타

| 분류 | 기술 | 설명 |
|------|------|------|
| **인증** | PyJWT + Bcrypt | JWT 토큰 기반 인증 |
| **문서 파싱** | PyMuPDF, python-docx | PDF, DOCX 파일 처리 |
| **이메일** | aiosmtplib | 비동기 SMTP 메일 전송 |
| **데이터 처리** | pandas, numpy, scikit-learn | 데이터 전처리 |

---

## 6. 프로젝트 구조

- [목차로 돌아가기](#목차)
  
```
deepnexus/
├── app/
│   ├── core/                           # 핵심 설정 및 인프라
│   │   ├── config.py                   # 환경 변수 관리 (pydantic-settings)
│   │   ├── database.py                 # PostgreSQL 비동기 엔진 및 세션
│   │   ├── dependencies.py             # FastAPI 의존성 (JWT 검증)
│   │   ├── orm.py                      # SQLAlchemy ORM 모델
│   │   ├── semantic_cache.py           # Redis 시맨틱 캐시 매니저
│   │   └── schema_inventory.json       # DB 테이블/컬럼 메타데이터
│   │
│   ├── graph/                          # LangGraph 워크플로우
│   │   ├── workflow.py                 # 그래프 정의 (노드, 엣지, 조건부 라우팅)
│   │   └── nodes.py                    # 노드 구현 (Router, SQL Agent, Vector Search, Generator)
│   │
│   ├── services/                       # 비즈니스 로직
│   │   ├── llm.py                      # LLM 및 임베딩 모델 초기화
│   │   ├── tools.py                    # SQL 실행(RLS), 하이브리드 검색, Reranking
│   │   ├── member.py                   # 회원가입/로그인 서비스
│   │   ├── memory.py                   # Redis 대화 기록 관리
│   │   ├── announcement_service.py     # 공지사항 서비스
│   │   ├── mail_service.py             # 메일 전송 서비스
│   │   └── meeting_service.py          # 회의실 예약 서비스
│   │
│   ├── schemas/                        # Pydantic 스키마
│   │   └── model.py                    # 요청/응답 모델, AgentState 정의
│   │
│   ├── models/                         # ML 모델
│   │   └── bge-reranker-onnx-int8/     # ONNX Reranker 모델
│   │
│   ├── utils/                          # 유틸리티
│   │   ├── file_parser.py              # 파일 파싱 (PDF, DOCX 등)
│   │   └── jwtUtils.py                 # JWT 토큰 유틸리티
│   │
│   ├── test/                           # 테스트 및 데이터 생성 스크립트
│   │   ├── generate_structured_vector.py
│   │   └── generate_unstructured_vector.py
│   │
│   └── main.py                         # FastAPI 진입점 (라우트 정의)
│
├── requirements.txt                    # Python 의존성
├── .env                                # 환경 변수 (Git 미추적)
└── README.md
```

---

## 7. API 엔드포인트

- [목차로 돌아가기](#목차)

### 인증

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/signup` | 회원가입 |
| `POST` | `/login` | 이메일 로그인 (JWT 발급) |
| `POST` | `/refresh` | Access Token 재발급 |

### AI 채팅

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/chat` | AI 채팅 (LangGraph 실행, SSE 스트리밍) |
| `POST` | `/stt` | 음성 → 텍스트 변환 |

### 공지사항

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET` | `/announcements` | 공지사항 목록 조회 |
| `POST` | `/announcements` | 공지사항 작성 |
| `GET` | `/announcements/{id}` | 공지사항 상세 조회 |

### 메일

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/mails/send` | 메일 전송 |
| `GET` | `/mails/sent` | 보낸 메일함 조회 |
| `DELETE` | `/mails/{id}` | 보낸 메일 삭제 |
| `GET` | `/address-book` | 주소록 조회 |

### 회의실 예약

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET` | `/meeting-rooms/reservations/monthly` | 월별 예약 현황 |
| `GET` | `/meeting-rooms/reservations/daily` | 일별/시간별 예약 현황 |
| `POST` | `/meeting-rooms/reservations` | 회의실 예약 |
| `DELETE` | `/meeting-rooms/reservations` | 예약 취소 |

---

## 8. 보안

- [목차로 돌아가기](#목차)
  
### JWT 인증

모든 API 요청은 **JWT Access Token** 검증을 거칩니다. 인증이 면제되는 경로는 `/login`, `/signup`, `/refresh`, `/docs`, `/openapi.json`, `/redoc`입니다.

### Row Level Security (RLS)

SQL 실행 시 사용자의 직급, 부서 코드, 상위 부서 코드를 **PostgreSQL 세션 변수**로 주입하여 행 수준 접근 제어를 적용합니다. 본인 권한 밖의 데이터 조회 시 "접근 권한이 없습니다" 안내를 반환합니다.

```
set_config('app.current_employee_id', ...)
set_config('app.current_dept_code', ...)
set_config('app.current_parent_dept_code', ...)
set_config('app.current_rank_level', ...)
```

### SQL Injection 방지

RLS 컨텍스트 값에 대해 영문자, 숫자, 언더바, 하이픈 외의 문자가 포함되면 즉시 예외를 발생시킵니다.

---

## 9. 인프라 및 배포

- [목차로 돌아가기](#목차)

### 배포 환경

본 프로젝트는 **Azure Container Apps**에 컨테이너 기반으로 배포되어 있습니다.

```
┌─────────────────────────────────────────────────────────┐
│                    Azure Cloud                          │
│                                                         │
│  ┌───────────────────┐    ┌──────────────────────────┐  │
│  │  Azure Container  │    │  Azure Database for      │  │
│  │  Apps             │◄──▶│  PostgreSQL               │  │
│  │  (FastAPI Server) │    │  + pgvector Extension    │  │
│  └────────┬──────────┘    └──────────────────────────┘  │
│           │                                             │
│           │               ┌──────────────────────────┐  │
│           └──────────────▶│  Azure Cache for Redis   │  │
│                           │  (Semantic Cache +       │  │
│                           │   Conversation Memory)   │  │
│                           └──────────────────────────┘  │
│                                                         │
│  ┌───────────────────┐    ┌──────────────────────────┐  │
│  │  Azure OpenAI     │    │  LangSmith               │  │
│  │  (GPT-4o,         │    │  (Tracing & Monitoring)  │  │
│  │   GPT-4o-mini)    │    │                          │  │
│  └───────────────────┘    └──────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 주요 Azure 리소스

| 리소스 | 용도 |
|--------|------|
| Azure Container Apps | FastAPI 서버 호스팅 (서버리스 컨테이너) |
| Azure Database for PostgreSQL | RDB + pgvector 벡터 저장소 |
| Azure Cache for Redis | 시맨틱 캐시 + 대화 메모리 |
| Azure OpenAI Service | GPT-4o / GPT-4o-mini LLM 추론 |

---

## 10. 환경 설정 및 실행 방법

- [목차로 돌아가기](#목차)
  
### 사전 요구사항

- Python 3.11+
- PostgreSQL 15+ (pgvector 확장 설치)
- Redis 7+ (Redis Stack 권장, Vector Search 지원)

### 1. 저장소 클론

```bash
git clone https://github.com/your-org/deepnexus.git
cd deepnexus
```

### 2. 가상 환경 생성 및 의존성 설치

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 항목을 설정합니다.

```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_DEPLOYMENT_GPT4O=gpt-4o
AZURE_DEPLOYMENT_GPT4O_MINI=gpt-4o-mini

# Embedding Model
EMBEDDING_MODEL_NAME=nlpai-lab/KURE-v1
EMBEDDING_DEVICE=cpu

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/deepnexus

# Redis
REDIS_URL=redis://localhost:6379

# LangSmith
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=deepnexus

# JWT
SECRET_KEY=your-secret-key

# SMTP
SMTP_SERVER=smtp.naver.com
SMTP_PORT=587
SMTP_USER=your-email@naver.com
SMTP_PASSWORD=your-smtp-password
```

### 4. 데이터베이스 설정

PostgreSQL에 pgvector 확장을 설치하고 필요한 테이블을 생성합니다.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 5. 벡터 데이터 생성

정형/비정형 데이터에 대한 벡터를 생성합니다.

```bash
# 정형 데이터 (DB 스키마) 벡터 생성
python -m app.test.generate_structured_vector

# 비정형 데이터 (문서) 벡터 생성
python -m app.test.generate_unstructured_vector
```

### 6. 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 정상 실행되면 아래 URL에서 API 문서를 확인할 수 있습니다.

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 11. 결과 및 성과

- [목차로 돌아가기](#목차)


### 동영상을 보려면 아래 썸네일 이미지를 클릭하세요.

[![Video Title](http://img.youtube.com/vi/CflJ6611RhA/0.jpg)](https://www.youtube.com/watch?v=CflJ6611RhA)

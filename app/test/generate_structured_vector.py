import sys
import os
import asyncio
import json
from sqlalchemy import text

# 프로젝트 루트 디렉토리를 시스템 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from app.core.database import AsyncSessionLocal
from app.services.llm import get_embeddings

async def insert_schema_data():
    print("🚀 스키마 데이터 적재 프로세스를 시작합니다...")
    
    # 1. 임베딩 모델 로드 (KURE-v1 등)
    embeddings = get_embeddings()
    print("✅ 임베딩 모델 로드 완료.")

    # 2. 전체 12개 테이블 메타데이터 정의
    # LLM이 스키마를 이해하는 데 필요한 모든 정보를 구조화합니다.
    schema_data = [
  {
    "table_name": "public.employee_tech_skills",
    "table_comment": "Technical skills and proficiency levels of employees",
    "column_list": [
      {
        "name": "tech_skill_id",
        "type": "integer",
        "comment": "Unique identifier for the skill record (PK)",
        "is_pkey": True
      },
      {
        "name": "employee_id",
        "type": "character varying(20)",
        "comment": "FK referencing the employee",
        "is_pkey": False
      },
      {
        "name": "skill_name",
        "type": "character varying(50)",
        "comment": "Name of the technology or skill (e.g., Python, AWS)",
        "is_pkey": False
      },
      {
        "name": "skill_category",
        "type": "character varying(20)",
        "comment": "Category of the skill (e.g., Backend, DevOps)",
        "is_pkey": False
      },
      {
        "name": "proficiency_level",
        "type": "character(1)",
        "comment": "Skill level code (L: Low, M: Mid, H: High, E: Expert)",
        "is_pkey": False
      },
      {
        "name": "years_of_experience",
        "type": "integer",
        "comment": "Years of experience with this skill",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.employee_tech_skills (tech_skill_id integer, employee_id character varying(20), skill_name character varying(50), skill_category character varying(20), proficiency_level character(1), years_of_experience integer);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.leave_usage_history",
    "table_comment": "Detailed log of each leave instance taken by employees",
    "column_list": [
      {
        "name": "history_id",
        "type": "integer",
        "comment": "Unique identifier for the usage record (PK)",
        "is_pkey": True
      },
      {
        "name": "employee_id",
        "type": "character varying(20)",
        "comment": "FK referencing the employee",
        "is_pkey": False
      },
      {
        "name": "leave_type_code",
        "type": "character varying(20)",
        "comment": "FK indicating the type of leave used",
        "is_pkey": False
      },
      {
        "name": "used_days_count",
        "type": "numeric(4,1)",
        "comment": "Number of days used (supports decimals for half-days)",
        "is_pkey": False
      },
      {
        "name": "start_date",
        "type": "date",
        "comment": "Start date of the leave",
        "is_pkey": False
      },
      {
        "name": "end_date",
        "type": "date",
        "comment": "End date of the leave",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.leave_usage_history (history_id integer, employee_id character varying(20), leave_type_code character varying(20), used_days_count numeric(4,1), start_date date, end_date date);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.client_companies",
    "table_comment": "Information about client companies and their contracts",
    "column_list": [
      {
        "name": "client_company_id",
        "type": "character varying(20)",
        "comment": "Unique client identifier (PK)",
        "is_pkey": True
      },
      {
        "name": "client_company_name",
        "type": "character varying(100)",
        "comment": "Name of the client company",
        "is_pkey": False
      },
      {
        "name": "partner_type",
        "type": "character varying(20)",
        "comment": "Type of partnership (e.g., Corporation, Public Sector)",
        "is_pkey": False
      },
      {
        "name": "business_registration_number",
        "type": "character varying(20)",
        "comment": "Business registration number",
        "is_pkey": False
      },
      {
        "name": "main_business_sector",
        "type": "character varying(50)",
        "comment": "Primary industry sector of the client",
        "is_pkey": False
      },
      {
        "name": "contact_person_name",
        "type": "character varying(50)",
        "comment": "Name of the primary contact person",
        "is_pkey": False
      },
      {
        "name": "contact_person_email",
        "type": "character varying(100)",
        "comment": "Email of the contact person",
        "is_pkey": False
      },
      {
        "name": "contact_person_phone",
        "type": "character varying(20)",
        "comment": "Phone number of the contact person",
        "is_pkey": False
      },
      {
        "name": "contract_status_code",
        "type": "character(1)",
        "comment": "Current contract status (N: None, S: Signed, Y: Completed)",
        "is_pkey": False
      },
      {
        "name": "internal_manager_employee_id",
        "type": "character varying(20)",
        "comment": "FK referencing the internal employee in charge",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.client_companies (client_company_id character varying(20), client_company_name character varying(100), partner_type character varying(20), business_registration_number character varying(20), main_business_sector character varying(50), contact_person_name character varying(50), contact_person_email character varying(100), contact_person_phone character varying(20), contract_status_code character(1), internal_manager_employee_id character varying(20));",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.tbl_deep_nexus_schema",
    "table_comment": None,
    "column_list": [
      {
        "name": "id",
        "type": "integer",
        "comment": None,
        "is_pkey": True
      },
      {
        "name": "table_name",
        "type": "character varying(100)",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "table_comment",
        "type": "text",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "column_list",
        "type": "jsonb",
        "comment": "컬럼 메타정보 리스트. 예: [{\"name\": \"user_id\", \"type\": \"varchar\", \"comment\": \"사번\", \"is_pkey\": True}]",
        "is_pkey": False
      },
      {
        "name": "ddl_content",
        "type": "text",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "sample_rows",
        "type": "jsonb",
        "comment": "테이블의 실제 데이터 샘플 (JSON 배열). 날짜 포맷이나 코드값 이해를 도움",
        "is_pkey": False
      },
      {
        "name": "schema_vector",
        "type": "vector(1024)",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "created_at",
        "type": "timestamp without time zone",
        "comment": None,
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.tbl_deep_nexus_schema (id integer, table_name character varying(100), table_comment text, column_list jsonb, ddl_content text, sample_rows jsonb, schema_vector vector(1024), created_at timestamp without time zone);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.tbl_deep_nexus_docs",
    "table_comment": None,
    "column_list": [
      {
        "name": "id",
        "type": "integer",
        "comment": None,
        "is_pkey": True
      },
      {
        "name": "file_id",
        "type": "character varying(255)",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "chunk_index",
        "type": "integer",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "doc_title",
        "type": "character varying(500)",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "doc_url",
        "type": "text",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "content",
        "type": "text",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "content_vector",
        "type": "vector(1024)",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "metadata",
        "type": "jsonb",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "permission_list",
        "type": "jsonb",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "version",
        "type": "character varying(100)",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "created_at",
        "type": "timestamp without time zone",
        "comment": None,
        "is_pkey": False
      },
      {
        "name": "updated_at",
        "type": "timestamp without time zone",
        "comment": None,
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.tbl_deep_nexus_docs (id integer, file_id character varying(255), chunk_index integer, doc_title character varying(500), doc_url text, content text, content_vector vector(1024), metadata jsonb, permission_list jsonb, version character varying(100), created_at timestamp without time zone, updated_at timestamp without time zone);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.meeting_room",
    "table_comment": "Master table for managing meeting room information. References generic room details used for reservations.",
    "column_list": [
      {
        "name": "meeting_room_id",
        "type": "character varying(10)",
        "comment": "Unique identifier or code for the meeting room (Primary Key, varchar)",
        "is_pkey": True
      },
      {
        "name": "room_name",
        "type": "character varying(10)",
        "comment": "Name of the meeting room (e.g., Conference Room A)",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.meeting_room (meeting_room_id character varying(10), room_name character varying(10));",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.departments",
    "table_comment": "Information about organizational departments with hierarchical structure",
    "column_list": [
      {
        "name": "department_code",
        "type": "character varying(10)",
        "comment": "Unique identifier for the department (PK)",
        "is_pkey": True
      },
      {
        "name": "department_name",
        "type": "character varying(50)",
        "comment": "Official name of the department",
        "is_pkey": False
      },
      {
        "name": "parent_department_code",
        "type": "character varying(10)",
        "comment": "Self-referencing FK pointing to the upper-level department (None for top-level)",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.departments (department_code character varying(10), department_name character varying(50), parent_department_code character varying(10));",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.job_ranks",
    "table_comment": "Standardized job ranks and their categories (e.g., Staff, Manager, Executive)",
    "column_list": [
      {
        "name": "job_rank_id",
        "type": "integer",
        "comment": "Unique numeric identifier for the job rank. Serves as the Primary Key (PK) and determines the hierarchical sort order.",
        "is_pkey": True
      },
      {
        "name": "job_rank_name",
        "type": "character varying(50)",
        "comment": "The official display title of the job position (e.g., Associate, Manager, Senior Manager).",
        "is_pkey": False
      },
      {
        "name": "job_rank_category",
        "type": "character varying(20)",
        "comment": "Broad classification used for defining Row-Level Security (RLS) policies and permission groups (e.g., Executive, Management, General).",
        "is_pkey": False
      },
      {
        "name": "job_rank_level",
        "type": "integer",
        "comment": "A specific numeric grade indicating seniority or pay scale structure, distinct from the sorting ID.",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.job_ranks (job_rank_id integer, job_rank_name character varying(50), job_rank_category character varying(20), job_rank_level integer);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.development_unit_prices",
    "table_comment": "Standard unit prices (labor costs) defined by department and rank",
    "column_list": [
      {
        "name": "unit_price_id",
        "type": "integer",
        "comment": "Unique identifier for the price record (PK)",
        "is_pkey": True
      },
      {
        "name": "department_code",
        "type": "character varying(10)",
        "comment": "FK referencing specific department",
        "is_pkey": False
      },
      {
        "name": "job_rank_id",
        "type": "integer",
        "comment": "FK referencing specific job rank",
        "is_pkey": False
      },
      {
        "name": "price_amount",
        "type": "numeric(15,2)",
        "comment": "Monetary value of the unit price",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.development_unit_prices (unit_price_id integer, department_code character varying(10), job_rank_id integer, price_amount numeric(15,2));",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.send_mail",
    "table_comment": "Table for storing sent email logs (Sent Box). RLS policies restrict access so users can only view emails they have sent.",
    "column_list": [
      {
        "name": "mail_id",
        "type": "integer",
        "comment": "Unique identifier for the sent mail (Primary Key, Serial)",
        "is_pkey": True
      },
      {
        "name": "receiver_email",
        "type": "character varying(100)",
        "comment": "Email address of the recipient",
        "is_pkey": False
      },
      {
        "name": "sender_email",
        "type": "character varying(100)",
        "comment": "Email address of the sender. Used for RLS policy to identify the owner of the record.",
        "is_pkey": False
      },
      {
        "name": "subject",
        "type": "character varying(200)",
        "comment": "Subject line of the email (Max 200 characters)",
        "is_pkey": False
      },
      {
        "name": "content",
        "type": "character varying",
        "comment": "Body content of the email (Variable length, supports HTML)",
        "is_pkey": False
      },
      {
        "name": "sent_at",
        "type": "timestamp without time zone",
        "comment": "Timestamp when the email was sent (Default: now())",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.send_mail (mail_id integer, receiver_email character varying(100), sender_email character varying(100), subject character varying(200), content character varying, sent_at timestamp without time zone);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.leave_types",
    "table_comment": "Definitions of various leave types available to employees",
    "column_list": [
      {
        "name": "leave_type_code",
        "type": "character varying(20)",
        "comment": "Unique code for the leave type (PK)",
        "is_pkey": True
      },
      {
        "name": "leave_type_name",
        "type": "character varying(50)",
        "comment": "Display name of the leave type",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.leave_types (leave_type_code character varying(20), leave_type_name character varying(50));",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.projects",
    "table_comment": "Details of projects managed by the company",
    "column_list": [
      {
        "name": "project_id",
        "type": "character varying(20)",
        "comment": "Unique project identifier (PK)",
        "is_pkey": True
      },
      {
        "name": "project_title",
        "type": "character varying(100)",
        "comment": "Title of the project",
        "is_pkey": False
      },
      {
        "name": "project_description",
        "type": "text",
        "comment": "Detailed description of the project scope",
        "is_pkey": False
      },
      {
        "name": "start_date",
        "type": "date",
        "comment": "Scheduled start date of the project",
        "is_pkey": False
      },
      {
        "name": "end_date",
        "type": "date",
        "comment": "Scheduled or actual end date of the project",
        "is_pkey": False
      },
      {
        "name": "is_completed",
        "type": "character(1)",
        "comment": "Status flag indicating if the project is finished (Y/N)",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.projects (project_id character varying(20), project_title character varying(100), project_description text, start_date date, end_date date, is_completed character(1));",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.employees",
    "table_comment": "Central repository for employee personal and employment data",
    "column_list": [
      {
        "name": "employee_id",
        "type": "character varying(20)",
        "comment": "Unique employee identifier (PK)",
        "is_pkey": True
      },
      {
        "name": "employee_name",
        "type": "character varying(50)",
        "comment": "Full name of the employee",
        "is_pkey": False
      },
      {
        "name": "phone_number",
        "type": "character varying(20)",
        "comment": "Contact phone number",
        "is_pkey": False
      },
      {
        "name": "job_rank_id",
        "type": "integer",
        "comment": "FK referencing job_ranks table",
        "is_pkey": False
      },
      {
        "name": "department_code",
        "type": "character varying(10)",
        "comment": "FK referencing departments table",
        "is_pkey": False
      },
      {
        "name": "home_address",
        "type": "character varying(255)",
        "comment": "Residential address of the employee",
        "is_pkey": False
      },
      {
        "name": "company_email",
        "type": "character varying(100)",
        "comment": "Official company email address (Unique)",
        "is_pkey": False
      },
      {
        "name": "login_password",
        "type": "character varying(255)",
        "comment": "Hashed password for system access",
        "is_pkey": False
      },
      {
        "name": "account_creation_date",
        "type": "date",
        "comment": "Date when the system account was created",
        "is_pkey": False
      },
      {
        "name": "gender_code",
        "type": "character(1)",
        "comment": "Gender code (M: Male, F: Female)",
        "is_pkey": False
      },
      {
        "name": "birth_date",
        "type": "date",
        "comment": "Date of birth",
        "is_pkey": False
      },
      {
        "name": "hire_date",
        "type": "date",
        "comment": "Official date of joining the company",
        "is_pkey": False
      },
      {
        "name": "resignation_date",
        "type": "date",
        "comment": "Date of resignation (None if currently employed)",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.employees (employee_id character varying(20), employee_name character varying(50), phone_number character varying(20), job_rank_id integer, department_code character varying(10), home_address character varying(255), company_email character varying(100), login_password character varying(255), account_creation_date date, gender_code character(1), birth_date date, hire_date date, resignation_date date);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.login_history",
    "table_comment": "Log of employee login activities for security auditing",
    "column_list": [
      {
        "name": "login_history_id",
        "type": "integer",
        "comment": "Auto-incrementing unique log ID (PK)",
        "is_pkey": True
      },
      {
        "name": "employee_id",
        "type": "character varying(20)",
        "comment": "FK referencing the employee who logged in",
        "is_pkey": False
      },
      {
        "name": "login_timestamp",
        "type": "timestamp without time zone",
        "comment": "Exact timestamp of the login event",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.login_history (login_history_id integer, employee_id character varying(20), login_timestamp timestamp without time zone);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.project_team_members",
    "table_comment": "Association table linking employees to projects",
    "column_list": [
      {
        "name": "project_id",
        "type": "character varying(20)",
        "comment": "FK referencing the project",
        "is_pkey": True
      },
      {
        "name": "employee_id",
        "type": "character varying(20)",
        "comment": "FK referencing the participating employee",
        "is_pkey": True
      },
      {
        "name": "assigned_timestamp",
        "type": "timestamp without time zone",
        "comment": "Timestamp when the employee was assigned to the project",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.project_team_members (project_id character varying(20), employee_id character varying(20), assigned_timestamp timestamp without time zone);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.announcement",
    "table_comment": "Table for managing company-wide announcements. Write permissions are controlled via RLS based on the author's upper-level department.",
    "column_list": [
      {
        "name": "announcement_id",
        "type": "integer",
        "comment": "Unique identifier for the announcement (Primary Key)",
        "is_pkey": True
      },
      {
        "name": "title",
        "type": "character varying(200)",
        "comment": "Title of the announcement (Max 200 characters)",
        "is_pkey": False
      },
      {
        "name": "content",
        "type": "character varying",
        "comment": "Body content of the announcement (Variable length, supports HTML)",
        "is_pkey": False
      },
      {
        "name": "parent_department_code",
        "type": "character varying(10)",
        "comment": "Upper-level department (Headquarters) code of the author, used for RLS write permission checks",
        "is_pkey": False
      },
      {
        "name": "employee_id",
        "type": "character varying(20)",
        "comment": "Employee ID of the initial author (References employees.employee_id)",
        "is_pkey": False
      },
      {
        "name": "created_at",
        "type": "timestamp without time zone",
        "comment": "Timestamp when the announcement was created (Default: now())",
        "is_pkey": False
      },
      {
        "name": "updated_at",
        "type": "timestamp without time zone",
        "comment": "Timestamp when the announcement was last updated",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.announcement (announcement_id integer, title character varying(200), content character varying, parent_department_code character varying(10), employee_id character varying(20), created_at timestamp without time zone, updated_at timestamp without time zone);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.reservation_meeting_room",
    "table_comment": "Table for meeting room reservations. RLS policies restrict deletion to the record owner and prohibit updates.",
    "column_list": [
      {
        "name": "reservation_id",
        "type": "integer",
        "comment": "Unique identifier for the reservation (PK, Serial)",
        "is_pkey": True
      },
      {
        "name": "meeting_room_id",
        "type": "character varying(10)",
        "comment": "ID of the reserved meeting room (References meeting_room)",
        "is_pkey": False
      },
      {
        "name": "employee_id",
        "type": "character varying(20)",
        "comment": "Employee ID of the reserver (Used for RLS delete permission check)",
        "is_pkey": False
      },
      {
        "name": "department_code",
        "type": "character varying(10)",
        "comment": "Department code of the reserver",
        "is_pkey": False
      },
      {
        "name": "usage_date",
        "type": "date",
        "comment": "Date when the meeting room will be used",
        "is_pkey": False
      },
      {
        "name": "start_time",
        "type": "integer",
        "comment": "Start time of the reservation (Integer format, e.g., 14 for 2PM)",
        "is_pkey": False
      },
      {
        "name": "reserved_at",
        "type": "timestamp without time zone",
        "comment": "Timestamp when the reservation was created (Default: now())",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.reservation_meeting_room (reservation_id integer, meeting_room_id character varying(10), employee_id character varying(20), department_code character varying(10), usage_date date, start_time integer, reserved_at timestamp without time zone);",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  },
  {
    "table_name": "public.annual_leave_quotas",
    "table_comment": "Summary of total and used leave days per employee per fiscal year",
    "column_list": [
      {
        "name": "fiscal_year",
        "type": "character(4)",
        "comment": "The fiscal year for the leave quota (YYYY)",
        "is_pkey": True
      },
      {
        "name": "employee_id",
        "type": "character varying(20)",
        "comment": "FK referencing the employee",
        "is_pkey": True
      },
      {
        "name": "total_leave_days",
        "type": "numeric(4,1)",
        "comment": "Total leave days allocated for the year",
        "is_pkey": False
      },
      {
        "name": "used_leave_days",
        "type": "numeric(4,1)",
        "comment": "Total leave days used so far",
        "is_pkey": False
      }
    ],
    "ddl_content": "CREATE TABLE public.annual_leave_quotas (fiscal_year character(4), employee_id character varying(20), total_leave_days numeric(4,1), used_leave_days numeric(4,1));",
    "sample_rows": [
      {
        "department_code": "HQ_MG",
        "department_name": "경영지원부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_SL",
        "department_name": "영업본부",
        "parent_department_code": None
      },
      {
        "department_code": "HQ_IT",
        "department_name": "기술연구소",
        "parent_department_code": None
      }
    ]
  }
]

    # 3. 데이터 Insert Loop
    async with AsyncSessionLocal() as session:
        
        # 기존 데이터 클리어
        await session.execute(text("TRUNCATE TABLE tbl_deep_nexus_schema RESTART IDENTITY"))
        
        for table in schema_data:
            # 3-1. 임베딩 텍스트 생성
            # 테이블명, 코멘트, 컬럼 정보를 자연스럽게 합쳐서 모델에게 전달
            columns_desc = ", ".join([f"{c['name']}({c['comment']})" for c in table['column_list']])
            text_for_vector = f"Table: {table['table_name']}\nDescription: {table['table_comment']}\nColumns: {columns_desc}"
            
            # 3-2. 벡터 생성 (API 비용 0원, 로컬 모델 사용)
            vector_values = await embeddings.aembed_query(text_for_vector)
            
            # 3-3. Insert
            insert_sql = text("""
                INSERT INTO tbl_deep_nexus_schema 
                (table_name, table_comment, column_list, ddl_content, sample_rows, schema_vector)
                VALUES 
                (:table_name, :table_comment, :column_list, :ddl_content, :sample_rows, :schema_vector)
            """)
            
            await session.execute(insert_sql, {
                "table_name": table["table_name"],
                "table_comment": table["table_comment"],
                "column_list": json.dumps(table["column_list"], ensure_ascii=False),
                "ddl_content": table["ddl_content"].strip(),
                "sample_rows": json.dumps(table["sample_rows"], ensure_ascii=False),
                "schema_vector": str(vector_values)
            })
            print(f"✅ Inserted: {table['table_name']}")
        
        await session.commit()
        print("🎉 모든 스키마 데이터가 성공적으로 적재되었습니다!")

if __name__ == "__main__":
    asyncio.run(insert_schema_data())
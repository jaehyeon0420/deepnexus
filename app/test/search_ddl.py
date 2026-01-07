import sys
import os
import asyncio
import json
from pathlib import Path
from typing import List, Literal
from pydantic import BaseModel, Field
from sqlalchemy import text
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

from app.core.database import AsyncSessionLocal
from app.services.llm import get_embeddings
from app.services.llm import get_llm


# Router의 출력 스키마 정의 (실제 앱과 동일)
class RouterOutput(BaseModel):
    intent: Literal["rdb", "vector", "both"] = Field(description="조회 경로")
    sql_keywords: List[str] = Field(description="핵심 키워드")
    vector_query: str = Field(description="유의어가 포함된 검색용 쿼리")

# JSON 파일에서 DB 스키마 인벤토리 로드
def get_schema_inventory_text() -> str:
    """JSON 파일을 읽어 LLM 프롬프트용 텍스트로 변환"""
    # 현재 파일 위치 기준으로 JSON 파일 경로 계산
    json_path = Path(project_root) / "app" / "core" / "schema_inventory.json"
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
        
        # LLM이 읽기 편한 리스트 형태로 변환
        inventory_lines = []
        for item in schema_data:
            line = f"- {item['table_name']}: {', '.join(item['column_list'])}"
            inventory_lines.append(line)
        
        return "\n".join(inventory_lines)
    except Exception as e:
        print(f"⚠️ 스키마 인벤토리 로드 실패: {e}")
        return "정보 없음"

async def get_optimized_query(raw_query: str) -> str:
    """LLM(Router)을 사용하여 질문을 검색용 쿼리로 최적화"""
    llm_gpt4o_mini = get_llm("gpt-4o-mini")

    actual_schema_context = get_schema_inventory_text()
    
    # Router 전용 프롬프트
    prompt = f"""
    당신은 프로페셔널한 시니어 로컬라이제이션 전문가, 스키마 리트리버, 의미론적 분석가 입니다.
    사용자의 질문을 분석하여 다음 세 가지 작업을 수행하세요:
    1. intent: 질문이 RDB(정형 데이터), Vector(비정형 문서/규정), 또는 Both(둘 다) 중 어디에 해당하는지 결정합니다.
    2. sql_keywords: SQL 생성을 위해 사용자 질문과 실제 테이블 스키마를 참고하여, 유사도가 높은 테이블 리스트를 출력하세요.
    3. vector_query: 벡터화된 비정형 데이터를 검색하기 위해, 사용자 질문에서 전문 용어, 유의어, 고유 명사를 포함한 최적의 벡터 쿼리를 생성하세요.

    ### 가이드라인:
    - 사용자가 '직급', '급여'를 언급하면 '연봉, 보너스, unit price, labor cost, 인건비' 등의 키워드를 확장하세요.
    - 사용자가 '기술', '능력'을 언급하면 'tech skill, proficiency, 스택, 경력' 등의 키워드를 확장하세요.
    - 불필요한 서술어(알려줘, 조회해 등)는 제거하고 의미가 담긴 명사 위주로 구성하세요.

    ### 실제 테이블 스키마
    {actual_schema_context}
    
    ### 예시 (Few-shot):
    질문: "인사팀 사람들의 직급별 단가 알려줘."
    결과: {{
        "intent": "rdb",
        "sql_keywords": ["departments", "development_unit_prices", "job_rank"],
        "vector_query": "인사팀 직급별 단가 departments price_amount job_rank_id MG_HR development_unit_prices"
    }}

    질문: "파이썬 능숙도가 높은 개발자 명단 보여줘"
    결과: {{
        "intent": "rdb",
        "sql_keywords": ["employee_tech_skills", "employees"],
        "vector_query": "사원 기술스택 숙련도 tech skill proficiency 파이썬"
    }}

    질문: "우리 회사 재택근무 규정이 어떻게 돼?"
    결과: {{
        "intent": "vector",
        "sql_keywords": [],
        "vector_query": "재택근무 원격근무 가이드라인 비대면근무 복지 규정 지침"
    }}

    질문: "사내 경조사비 지급 규정이랑 신청 절차가 어떻게 되는지 가이드라인에서 찾아줘."
    결과: {{
        "intent": "vector",
        "sql_keywords": [],
        "vector_query": "경조사비 지급 기준 신청 방법 경조금 가이드라인 복리후생 규정 지침"
    }}

    질문: "미래금융지주 프로젝트에 참여 중인 인원들 중에서 AWS나 클라우드 관련 기술 스택을 가진 전문가가 누구인지 알려줘."
    결과: {{
        "intent": "rdb",
        "sql_keywords": ["projects", "project_team_members", "employee_tech_skills", "employees"],
        "vector_query": "고객사 프로젝트 투입 인원 기술 역량 클라우드 전문가 tech skill proficiency client_companies projects"
    }}
    사용자 질문: {raw_query}
    """
    
    # 구조화된 출력 유도
    structured_llm = llm_gpt4o_mini.with_structured_output(RouterOutput)
    result = await structured_llm.ainvoke(prompt)
    
    print(f"   [Router 분석 결과]: {result.sql_keywords}")
    
    return " ".join(result.sql_keywords)

async def search_schema_test(raw_query: str):
    print(f"\n🚀 [원본 질문]: {raw_query}")
    
    async with AsyncSessionLocal() as session:
        try:
            # [단계 1] LLM을 통한 쿼리 최적화 (이 부분이 핵심!)
            optimized_query = await get_optimized_query(raw_query)
            
            # [단계 2] 최적화된 쿼리를 벡터로 변환
            embeddings_model = get_embeddings()
            print("   ...최적화 쿼리 임베딩 중...")
            query_vector = await embeddings_model.aembed_query(optimized_query)
            
            # [단계 3] DB 검색
            search_sql = text("""
                SELECT 
                    table_name, 
                    table_comment, 
                    1 - (schema_vector <=> :vector) AS similarity
                FROM tbl_deep_nexus_schema
                ORDER BY similarity DESC
                LIMIT 3;
            """)
            
            result = await session.execute(search_sql, {"vector": str(query_vector)})
            rows = result.fetchall()
            
            print("\n" + "="*60)
            print("🔍 LLM 추천 스키마 결과 (Router 최적화 적용)")
            print("="*60)
            
            for i, row in enumerate(rows):
                print(f"[{i+1}] 테이블: {row[0]} | 유사도: {row[2]:.4f}")
                print(f"    설명: {row[1][:100]}...")
                print("-" * 60)
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")

async def main():
    test_queries = [
        "개발팀 올해 연차 사용 현황 보여줘.",
        "우리 회사 파이썬 전문가가 누구야?",
        "인사팀 인원수 좀 알려줘"
    ]
    
    for query in test_queries:
        await search_schema_test(query)

if __name__ == "__main__":
    asyncio.run(main())
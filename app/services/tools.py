from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.services.llm import get_embeddings
import json
from sentence_transformers import CrossEncoder
import re
import time
import torch
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer


# 임베딩(자연어 => 벡터) 모델 : KURE-v1
embeddings = get_embeddings()

# Reranker(상위 10개 문서 추출) 모델
ONNX_MODEL_DIR = "app/models/bge-reranker-onnx-int8"
onnx_tokenizer = AutoTokenizer.from_pretrained(ONNX_MODEL_DIR)
onnx_model = ORTModelForSequenceClassification.from_pretrained(
    ONNX_MODEL_DIR, 
    provider="CPUExecutionProvider"
)

# Text-to-SQL용 키워드(optimized_sql_keywords)를 바탕으로 RDB 스키마 벡터 검색 후 DDL 추출
async def search_schema_and_get_ddl(query_text: str) -> str:
    # 자연어 => 벡터 변환
    query_vector = await embeddings.aembed_query(query_text)
    
    # 벡터 유사도 검색으로 상위 5개 DDL 추출
    async with AsyncSessionLocal() as session:
        stmt = text("""
            SELECT ddl_content 
            FROM tbl_deep_nexus_schema
            ORDER BY schema_vector <=> :vector LIMIT 5
        """)
        result = await session.execute(stmt, {"vector": str(query_vector)})
        rows = result.fetchall()
        return "\n\n".join([row[0] for row in rows])

    
# SQL Injection 공격 차단을 위한 RLS 컨텍스트 값 검증
def validate_security_context(value: str | int) -> str:
    str_val = str(value)
    
    # 영문자, 숫자, 언더바, 하이픈 외의 문자 발견 시 예외 발생
    if not re.match(r"^[a-zA-Z0-9_\-]+$", str_val):
        raise ValueError(f"Security Alert: Invalid context value detected -> {str_val}")
    return str_val

# 생성된 SQL 실행(RLS 적용)
import json
from sqlalchemy import text

async def execute_sql_query(sql: str, employee_id: str, department_code: str, parent_department: str, job_rank_id: str) -> str:
    try:
        # 1. 입력값 검증 (SQL Injection 방지)
        safe_employee = validate_security_context(employee_id)
        safe_dept = validate_security_context(department_code)
        safe_parent = validate_security_context(parent_department)
        safe_rank = validate_security_context(job_rank_id)
        
        #print(f"safe_employee : {safe_employee}, safe_dept : {safe_dept}, safe_parent : {safe_parent}, safe_rank : {safe_rank}")
        
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

    async with AsyncSessionLocal() as session:
        try:
            # 2. 하나의 트랜잭션으로 실행 (SET LOCAL의 유효 범위 보장)
            async with session.begin():
                
                # 3. 다중 RLS 세션 변수 주입 (set_config 활용)
                set_context_sql = text("""
                    SELECT 
                        set_config('app.current_employee_id', :emp, true),
                        set_config('app.current_dept_code', :dept, true),
                        set_config('app.current_parent_dept_code', :p_dept, true),
                        set_config('app.current_rank_level', :rank, true);
                """)
                
                await session.execute(set_context_sql, {
                    "emp": safe_employee,
                    "dept": safe_dept,
                    "p_dept": safe_parent,
                    "rank": safe_rank
                })
                
                # 4. LLM이 생성한 메인 SQL 실행
                result = await session.execute(text(sql))
                columns = result.keys()
                rows = result.fetchall()
                
                # 5. 결과가 0건일 경우 권한 체크
                if not rows:
                    # SELECT 쿼리인 경우에만 쉐도우 카운트 진행 (DML 사이드 이펙트 방지)
                    if sql.strip().upper().startswith("SELECT"):
                        # LLM이 생성한 SQL 마지막 세미콜론 제거
                        clean_sql = sql.strip().rstrip(';')
                        
                        shadow_check = await session.execute(
                            text("SELECT fn_check_query_count_bypass_rls(:query)"),
                            {"query": clean_sql}
                        )
                        shadow_count = shadow_check.scalar()
                        
                        if shadow_count > 0:
                            return json.dumps({
                                "status": "forbidden",
                                "message": "데이터가 존재하지만, 현재 사용자의 권한(직급/부서)으로는 접근할 수 없습니다."
                            }, ensure_ascii=False)
                        else:
                            return json.dumps({
                                "status": "not_found",
                                "message": "요청하신 조건에 부합하는 데이터가 시스템에 존재하지 않습니다."
                            }, ensure_ascii=False)
                    
                    return json.dumps([], ensure_ascii=False)

                # 6. 정상 결과 반환
                data = [dict(zip(columns, row)) for row in rows]
                return json.dumps(data, ensure_ascii=False, default=str)
                
        except Exception as e:
            return json.dumps({"status": "error", "message": f"SQL Execution Error: {str(e)}"}, ensure_ascii=False)

# 비정형 데이터에 대한 하이브리드(키워드 + 벡터) 검색 수행 -> 상위 5개 문서 반환
async def hybrid_vector_search(query_text: str, department_code: str, filter_keywords: list[str]) -> str:
    #total_start = time.perf_counter()
    
    # 1. 임베딩 생성
    #step1_start = time.perf_counter()
    query_vector = await embeddings.aembed_query(query_text)
    #print(f"⏱️ [Step 1: Embedding] {time.perf_counter() - step1_start:.4f} sec")
    
    async with AsyncSessionLocal() as session:
        try:
            # 2. DB 설정 최적화
            #step2_start = time.perf_counter()
            await session.execute(text("SET LOCAL jit = off"))
            
            #print(f"⏱️ [Step 2: DB Config] {time.perf_counter() - step2_start:.4f} sec")
            
            # 3. 벡터 검색 HNSW 인덱스 사용
            #step3_start = time.perf_counter()
            vector_sql = text("""
                SELECT content, metadata, doc_url, doc_title, (1 - (content_vector <=> :vector)) as sim_score
                FROM tbl_deep_nexus_docs
                ORDER BY content_vector <=> :vector ASC
                LIMIT 15
            """)
            
            vector_result = await session.execute(vector_sql, {"vector": str(query_vector)})
            vector_rows = vector_result.fetchall()
            #print(f"⏱️ [Step 3: Vector Search] {time.perf_counter() - step3_start:.4f} sec (Found: {len(vector_rows)})")
            
            # 4. 키워드 검색 GIN 인덱스 사용
            #step4_start = time.perf_counter()
            keyword_rows = []
            if filter_keywords:
                safe_keywords = [f"'%{kw.replace("'", "''")}%'" for kw in filter_keywords]
                array_literal = ", ".join(safe_keywords)
                
                keyword_sql = text(f"""
                    SELECT content, metadata, doc_url, doc_title,0.0 as sim_score
                    FROM tbl_deep_nexus_docs
                    WHERE content ILIKE ANY(ARRAY[{array_literal}])
                    LIMIT 15
                """)
                keyword_result = await session.execute(keyword_sql)
                keyword_rows = keyword_result.fetchall()
            #print(f"⏱️ [Step 4: Keyword Search] {time.perf_counter() - step4_start:.4f} sec (Found: {len(keyword_rows)})")
            
            # 5. 결과 병합 및 중복 제거
            #step5_start = time.perf_counter()
            unique_docs = {}
            for row in vector_rows:
                unique_docs[row.content] = row
            for row in keyword_rows:
                if row.content not in unique_docs:
                    unique_docs[row.content] = row
            combined_rows = list(unique_docs.values())
            #print(f"⏱️ [Step 5: Merge] {time.perf_counter() - step5_start:.4f} sec (Total: {len(combined_rows)})")
            
            if not combined_rows:
                return "검색 결과가 없습니다."

            # 6. Reranking
            #step6_start = time.perf_counter()
            documents = [row.content for row in combined_rows]
            pairs = [[query_text, doc] for doc in documents]
            
            # ONNX 추론 로직 적용
            inputs = onnx_tokenizer(
                pairs, padding=True, truncation=True, return_tensors="pt", max_length=256
            )
            with torch.no_grad():
                outputs = onnx_model(**inputs)
                scores = outputs.logits.view(-1,).float().tolist()
            
            # 점수 높은 순 정렬
            scored_docs = sorted(zip(scores, combined_rows), key=lambda x: x[0], reverse=True)
            
            # 상위 3개 선택
            top_k = scored_docs[:3]
            formatted_docs = []
            for score, row in top_k:
                formatted_docs.append(
                    f"- 내용 : {row.content}\n- 파일명 : {row.doc_title}\n- 출처 : {row.doc_url}\n"
                )
            #print(f"⏱️ [Step 6: Reranking (ONNX)] {time.perf_counter() - step6_start:.4f} sec")
            
            #print(f"🚀 [Total Latency] {time.perf_counter() - total_start:.4f} sec")
            return "\n\n".join(formatted_docs)
            
        except Exception as e:
            return f"Error: {str(e)}"            
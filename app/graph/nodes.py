from app.schemas.model import AgentState, RouterOutput
from app.services.llm import get_llm
from app.services.tools import search_schema_and_get_ddl, execute_sql_query, hybrid_vector_search
from langchain_core.prompts import ChatPromptTemplate
import json
from pathlib import Path
import os

# 프로젝트 루트 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))

llm_gpt4o = get_llm("gpt-4o")
llm_gpt4o_mini = get_llm("gpt-4o-mini")

# JSON 파일에서 DB 스키마 인벤토리 로드
def get_schema_inventory_text() -> str:
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
        print(f"스키마 인벤토리 로드 실패: {e}")
        return "정보 없음"
    
    
# 1. 정형/비정형 경로 설정
async def router_node(state: AgentState):
    # DB 스키마 JSON
    actual_schema_context = get_schema_inventory_text()
    
    # 사용자 업로드 파일 유무
    file_content = state.get("file_context", "")
    is_file_uploaded = bool(file_content and file_content.strip())
    
    # 사용자 <> LLM 답변 이전 대화 기록 정보
    history = state.get("history", "")
    recent = history[-2:]  # 이전 기록 중, 질문-답변 1쌍만 추출
    formatted = []
    for msg in recent:
        role = "이전 질문" if msg["role"] == "user" else "이전 답변"
        formatted.append(f"{role}: {msg['content']}")
    
    last_history = "\n".join(formatted)
    
    prompt = ChatPromptTemplate.from_template("""
        당신은 프로페셔널한 시니어 데이터 아키텍트이자 의미론적 검색 전문가입니다.
        사용자의 이전 대화 기록 및 질문을 분석하여 [intent, sql_keywords, vector_query]를 결정하세요.
        사용자의 현재 질문에 '그', '그것', '이전'과 같은 표현이 있다면 이전 대화 기록을 참고하여, intent를 결정하세요.
        
        ### 1. Intent 결정 로직 (우선순위 순서대로 판단하세요)

        1순위. 'other' (파일 우선 원칙)
        - 조건: 'is_file_uploaded'가 True이면서, 질문이 첨부된 파일의 내용 분석, 요약, 번역, 가공을 요청하는 경우.
        - 주의: 파일 내용이 설령 회사 규정이나 데이터처럼 보여도, 외부 DB 조회가 아닌 "이 파일 안에서 해결"하는 것이라면 무조건 'other'입니다.

        2순위. 'rdb'
        - 조건: 사내 DB(테이블 스키마 참조)에서 특정 수치, 통계, 명단 조회가 필요한 경우.

        3순위. 'vector'
        - 조건: 사내 규정, 가이드라인, 절차 등 문서 기반의 비정형 지식 검색이 필요한 경우
        
        4순위. 'both'
        - 조건: RDB의 정형 데이터와 Vector의 규정을 모두 확인해야만 답변이 가능한 복합 질문인 경우.
        
        ### 1.1 [이전 대화 기록]
        - {last_history}

        
        ### 2. 추가 필드 가이드라인
        - sql_keywords: intent가 rdb/vector/both일 때만 추출 (other일 때는 빈 리스트 [])
        - vector_query: intent가 rdb/vector/both일 때만 생성 (other일 때는 빈 문자열 "")
        
        ### 3. sql_keywords: 검색 엔진의 'Hard Filter' 역할을 합니다. 
        - RDB 조회 시: 관련도가 높은 '테이블명'과 '컬럼명'을 추출하세요.
        - Vector 조회 시: 문서 제목이나 본문에 반드시 포함되어야 할 '도메인 핵심 명사'를 추출하세요. (예: 규정, 수칙, 신청절차, 재택, 경조사 등)
        - 이는 검색 성능을 높이기 위한 필터링 키워드로 사용되므로 매우 중요합니다.

        ### 4. vector_query: 의미 기반 검색을 위해 전문 용어와 유의어를 포함한 서술형 검색어를 생성하세요.
        - 사용자가 '돈, 급여, 단가'를 언급하면 'salary, unit price, labor cost, 인건비' 등으로 확장하세요.
        - 사용자가 '기술, 스택'을 언급하면 'tech skill, proficiency, expertise' 등으로 확장하세요.
        - 명사 위주로 구성하되, 질문의 핵심 의도를 담은 영문 용어를 반드시 섞으세요.
        - 단, 사용자가 업로드한 파일이 존재하고, 업로드한 파일에 대해서만 처리를 요청한다면 intent를 other로 반환하세요.

        ### 실제 테이블 스키마 Reference:
        {actual_schema_context}
        
        ### 예시 (Few-shot):
        질문: "첨부한 파일 분석해서 보고서 생성해줘."
        결과: {{
            "intent": "other",
            "sql_keywords": [],
            "vector_query": ""
        }}
        
        질문: "업로드 파일 분석해줘."
        결과: {{
            "intent": "other",
            "sql_keywords": [],
            "vector_query": ""
        }}
        
        질문: "인사팀 사람들의 직급별 단가 알려줘."
        결과: {{
            "intent": "rdb",
            "sql_keywords": ["departments", "development_unit_prices", "job_ranks", "price_amount"],
            "vector_query": "인사팀 부서별 직급 단가 인건비 unit price labor cost job rank"
        }}

        질문: "우리 회사 재택근무 규정이 어떻게 돼? 나도 대상자인지 알려줘."
        결과: {{
            "intent": "both",
            "sql_keywords": ["employees", "departments", "재택근무", "운영지침", "근무수칙"],
            "vector_query": "재택근무 원격근무 대상자 자격 가이드라인 비대면근무 복지 규정 remote work policy"
        }}

        질문: "경조사비 지급 규정이랑 내 신청 이력 보여줘."
        결과: {{
            "intent": "both",
            "sql_keywords": ["leave_usage_history", "경조사비", "지급기준", "복리후생", "신청절차"],
            "vector_query": "경조금 지급 기준 경조사비 신청 절차 가족 수당 가이드라인 benefit policy"
        }}

        질문: "회사 보안 지침 중에서 외부 장비 반입 절차 설명해줘."
        결과: {{
            "intent": "vector",
            "sql_keywords": ["보안지침", "외부장비", "반입절차", "승인프로세스", "보안수칙"],
            "vector_query": "외부 기기 반입 보안 승인 절차 자산 반출입 가이드라인 IT security policy asset management"
        }}

        질문: "파이썬 숙련도가 '상'인 개발자들 명단이랑 관련 스택 우대 규정 찾아줘."
        결과: {{
            "intent": "both",
            "sql_keywords": ["employee_tech_skills", "employees", "proficiency_level", "기술역량", "우대사항"],
            "vector_query": "파이썬 개발자 기술 숙련도 우대 규정 역량 평가 가이드라인 python tech skill proficiency criteria"
        }}
        
        ----------------------
        ### 현재 세션 정보
        - 사용자 업로드 파일 존재 여부 (is_file_uploaded): {is_file_uploaded}
        - 사용자 질문: {question}
        - 첨부 파일 내용 (참고용): {file_context}
    """)
    
    chain = prompt | llm_gpt4o_mini.with_structured_output(RouterOutput)
    
    # 질문 분석 후, RouterOutput 스키마에 맞게 구조화된 출력 생성
    raw_result = await chain.ainvoke({
        "question": state["question"], 
        "actual_schema_context" : actual_schema_context,
        "file_context": file_content if is_file_uploaded else "첨부 파일 없음",
        "is_file_uploaded": is_file_uploaded,
        "last_history": last_history
    })
    
    # 딕셔너리로 변환
    result = raw_result.model_dump()
    
    #print(f"Router Node Output : {result}")
    
    return {
        "intent": result["intent"], 
        "optimized_sql_keywords": result["sql_keywords"],
        "optimized_vector_query": result["vector_query"]
    }
    
    
# 2. 정형 데이터 처리(RDB Schema 조회 -> SQL 생성 -> SQL 실행)
from pydantic import BaseModel, Field

# SQL 실행 출력을 구조화 하기 위한 스키마 정의
class SQLGenerationResponse(BaseModel):
    thought: str = Field(description="SQL을 작성하기 위한 논리적 추론 과정")
    sql: str = Field(description="최종 PostgreSQL 쿼리")

async def sql_agent_node(state: AgentState):
    query_keywords = " ".join(state["optimized_sql_keywords"])
    
    # 유사도 높은 상위 5개 테이블에 대한 DDL 추출
    ddl_context = await search_schema_and_get_ddl(query_keywords)
    
    # SQL 재시도 횟수
    max_retries = 3 
    
    # 이전 에러 메시지 저장용
    last_error = ""
    
    # 구조화된 출력 적용
    structured_llm = llm_gpt4o.with_structured_output(SQLGenerationResponse)
    
    # DB 스키마 JSON
    actual_schema_context = get_schema_inventory_text()
    
    # 사용자 <> LLM 답변 이전 대화 기록 정보
    history = state.get("history", "")
    recent = history[-4:]  # 이전 기록 중, 질문-답변 2쌍만 추출
    formatted = []
    for msg in recent:
        role = "이전 질문" if msg["role"] == "user" else "이전 답변"
        formatted.append(f"{role}: {msg['content']}")
    
    last_history = "\n".join(formatted)

    for i in range(max_retries):
        retry_msg = f"\n\n[이전 쿼리 에러 보고]\n{last_error}\n위 에러를 분석하여 동일한 실수를 반복하지 마세요." if last_error else ""
        
        # CoT + Few-shot 프롬프트        
        prompt = f"""
        당신은 복잡한 전사적 자원 관리(ERP) 시스템의 PostgreSQL 전문가입니다. 
        제공된 DDL과 사용자 질문을 바탕으로 최적의 SQL을 생성하세요.

        ### [준칙]
        1. Chain-of-Thought: SQL을 작성하기 전, 질문을 해결하기 위한 단계별 논리를 'thought' 필드에 먼저 정리하세요.
        2. Dialect: PostgreSQL 문법을 준수하며, 가독성을 위해 Alias(별칭)를 반드시 사용하세요.
        3. Logic: 인사/급여 관련 쿼리 시 '퇴직자(resignation_date)' 제외 여부를 질문의 맥락에 따라 판단하세요.
        4. Join: 조인 시 반드시 테이블 간의 관계(FK)를 DDL에서 확인하세요.
        5. 명칭이나 이름값이 필요한 경우 코드(부서코드, 직급코드, 휴가구분코드) 대신 원장(마스터) 테이블에서 한글 명칭을 조회하도록 쿼리를 작성하세요.

        ### [Few-shot 예시]
        질문: "인사팀 대리급 직원들의 올해 예상 연봉 총합 보여줘."
        Thought: 1. employees 테이블과 development_unit_prices 조인 필요. 
                 2. departments에서 인사팀 코드 확인. 
                 3. unit_price에 12를 곱해 연봉 계산. 
                 4. sum 함수로 합산.
        SQL: SELECT SUM(d.price_amount * 12) as total_annual_salary 
             FROM public.employees e 
             JOIN public.development_unit_prices d ON e.job_rank_id = d.job_rank_id AND e.department_code = d.department_code
             WHERE e.department_code = 'MG_HR' AND e.job_rank_id = 4 AND e.resignation_date IS NULL;

        ### [컨텍스트]
        - 사용자 사원 ID(employee_id) : {state['employee_id']}
        - 사용자 직급 ID : {state['job_rank_id']}
        - 사용자 부서 코드 : {state['department_code']}
        - 사용자 상위 부서 코드 : {state['parent_department']}
        - 사용자 사내 이메일 : {state['company_email']}
        
        - 전체 테이블 스키마
        {actual_schema_context}
        
        - SQL 생성 시, 참고해야하는 유사도 높은 상위 5개 테이블의 DDL:
        {ddl_context}
        {retry_msg}

        ### [질문]
        {state["question"]}
        
        ### [사용자 대화 이전 기록]
        - 사용자가 새로운 조건을 명시하지 않고 "다시 보여줘" 또는 "필터링해줘"라고 한다면, 이전 대화 기록을 참고하여 SQL을 생성하세요.
        {last_history}
        """

        # LLM 호출
        raw_response = await structured_llm.ainvoke(prompt)
        response = raw_response.model_dump() 
        
        # 로그 출력 
        #print(f"  [Thought]: {response['thought']}")
        #print(f"  [Generated SQL]: {response['sql']}")

        # 실행
        result = await execute_sql_query(
            response['sql'],
            state['employee_id'],
            state["department_code"], 
            state["parent_department"], 
            state["job_rank_id"]
        )

        # 정상 실행 시, 결과 반환
        if "Error:" not in result:
            return {"rdb_result": result, "generated_sql": response['sql']}
        
        last_error = f"쿼리: {response['sql']} \n에러 메시지: {result}"
        print(f" !! [Retry {i+1}] 에러 발생: {result}")

    return {"rdb_result": "SQL 실행 실패. 관리자에게 문의하세요."}

# 2. 비정형 데이터 처리 
async def vector_search_node(state: AgentState):
    # Router가 생성한 서술형 검색어
    query = state["optimized_vector_query"]
    
    # sql_keywords: Router가 추출한 핵심 명사들 (필터링용)
    filter_keywords = state.get("optimized_sql_keywords", [])
    
    # 하이브리드 검색 수행 (Nori, pg_trgm, Rerank 로직은 tools.py 내장)
    docs = await hybrid_vector_search(query, state["department_code"], filter_keywords)
    
    return {"vector_result": docs}

# 3. 정형 데이터 결과 + 비정형 데이터 결과 => 최종답변 생성
async def generator_node(state: AgentState):
    rdb_data = state.get("rdb_result", "")
    vector_data = state.get("vector_result", "")
    file_context = state.get("file_context", "")
    
    # 컨텍스트 길이에 따른 모델 선택 로직
    context_length = len(str(rdb_data)) + len(str(vector_data))
    target_llm = llm_gpt4o if context_length > 15000 else llm_gpt4o_mini
    
    # 사용자 <> LLM 답변 이전 대화 기록 정보
    history = state.get("history", "")
    formatted = []
    for msg in history:
        role = "이전 질문" if msg["role"] == "user" else "이전 답변"
        formatted.append(f"{role}: {msg['content']}")
    
    full_history = "\n".join(formatted)
    
    prompt = f"""
    당신은 기업 내부 정보 전문가입니다.
    제공된 [정형 데이터], [비정형 문서], [사용자 이전 대화 기록]을 바탕으로 직원의 질문에 친절하고 정확하게 답변하세요.

    ### [답변 가이드라인]
    1. 종합 답변: 정형 데이터(숫자/현황)와 비정형 데이터(규정/절차)를 결합하여 하나의 완성된 문장으로 답하세요.
    2. 가독성: 중요한 수치나 리스트는 마크다운 표(Table)나 불렛포인트(Bullet)를 활용하세요. 단 ###이나 **은 절대 작성하지 마세요.
    3. 부족한 정보: 조회된 정보로 답변이 불충분할 경우, 추측하지 말고 추가로 확인이 필요한 사항을 안내하세요.
    4. 만약, 정형/비정형 데이터가 존재하지 않고, 업로드한 파일에 대해서만 분석 또는 처리를 요청한다면 사용자가 요청한 사항에 맞게 수행하세요.
    5. 만약, 정형/비정형 데이터가 존재하고, 업로드한 파일이 존재한다면 결과 데이터와 파일 내용을 엮어 자연스럽게 답변하세요.
    
    ### [금지 밀 권장사항]
    1. 코드값 노출 금지: 'MG_HR', 'HQ_MG', 'LV_HALF_AM'와 같은 시스템 코드나 부서 코드를 답변에 직접 노출하지 마세요. 
    - 대신 '인사팀', '본사 관리부문' 등 질문의 맥락에 맞는 한글 명칭으로 순화하세요.
    2. 사용자 친화적 명칭: 데이터에 'emp036' 같은 ID만 있고 이름이 없다면 'ID: emp036 직원' 식으로 표현하되, 가급적 자연스러운 문장으로 구성하세요.
    3. 비정형 문서의 결과가 '검색 결과가 없습니다.'인 경우, 해당 문구를 그대로 답변에 포함하지 마세요. 대신 '관련 규정을 찾지 못했습니다.' 등으로 자연스럽게 안내하세요.
    4. 정형 데이터의 status가 forbidden인 경우 '해당 데이터에 대한 접근 권한이 없습니다.'라고 안내하세요.

    [정형 데이터 (RDB)]
    {rdb_data if rdb_data else "조회된 데이터 없음"}

    [비정형 문서 (Vector)]
    {vector_data if vector_data else "관련 규정 못 찾음"}

    [사용자 업로드 파일(file) 내용]
    {file_context if file_context else "사용자 업로드 파일 없음"}
    
    [사용자 이전 대화 기록]
    {full_history}
    
    [사용자 질문]
    {state["question"]}
     
    [답변 형식]   
    1. 내용
    - 사용자 이전 대화기록을 참고하여 톤 및 매너를 동일하게 유지하세요.
    - 데이터 성격에 따라 표, 리스트 또는 문단 형식 중 최적의 방식으로 작성하세요.
    - 비정형 문서에서 추출한 데이터라면 사실 기반으로 자연스러운 서술형으로 작성하세요.
    - 비정형 문서에 추출 시, 보고서명 또는 규정명을 밝히며 상세 설명을 덧붙입니다.
    - 답변에 마크다운(###, **)을 포함하지 마세요. 표 또는 불릿은 가능합니다.
    2. 출처
    - 비정형 문서에서 검색한 경우에만 '[출처 : 문서명](URL)' 형식으로 출처를 명확히 밝히세요.
    """
    
    full_content = ""
    
    async for chunk in target_llm.astream(prompt):
        #if first_token_time is None and chunk.content == '###':
        #    first_token_time = time.perf_counter() - start_llm
        #    print(f"⏱️ [Generator Step 2: TTFT] {first_token_time:.4f} sec, content : {chunk.content}") # 첫 토큰 시간 측정
        
        full_content += chunk.content

    #print(f"⏱️ [Generator Step 3: Total Generation] {time.perf_counter() - start_llm:.4f} sec") # 디버깅 추가
    # ------------------------------------------------------------------
    
    #print(f"🚀 [Generator Total] {time.perf_counter() - start_total:.4f} sec") # 디버깅 추가
    return {"final_answer": full_content}

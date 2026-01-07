import re
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.schemas.model import LoginRequest, MemberInfo, TokenInfo, LoginResponse
from app.utils.jwtUtils import JwtUtils

# 비밀번호 암호화 설정 (단방향 해시 함수 Bcrypt 사용)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class MemberService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # 비밀번호 해싱 함수
    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    # 사원 ID 생성 로직 (emp033 -> +1 -> emp034)
    async def generate_employee_id(self) -> str:
        
        # 가장 최근 employee_id 조회
        query = text("SELECT employee_id FROM employees ORDER BY employee_id DESC LIMIT 1")
        result = await self.session.execute(query)
        last_id_row = result.fetchone()

        if not last_id_row:
            return "emp001" # 데이터가 하나도 없으면 001부터 시작

        last_id = last_id_row[0] # 예: emp064

        # 숫자 부분 추출 (정규표현식으로 숫자만 추출)
        match = re.search(r'\d+', last_id)
        if match:
            number_part = int(match.group())
            new_number = number_part + 1
            # 다시 emp + 3자리 숫자(0 채움) 포맷팅
            return f"emp{str(new_number).zfill(3)}"
        else:
            # 예외 상황: 형식이 안 맞을 경우 기본 처리
            raise HTTPException(status_code=500, detail="사원 ID 생성 중 오류가 발생했습니다.")

    # 회원가입 메인 로직
    async def create_employee(self, data: dict):
        try:
            # 이메일 중복 체크
            check_email_query = text("SELECT 1 FROM employees WHERE company_email = :email")
            existing_email = await self.session.execute(check_email_query, {"email": data.company_email})
            if existing_email.fetchone():
                raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다.")

            # 사원 ID 생성
            new_emp_id = await self.generate_employee_id()
            print(f"new_emp_id : {new_emp_id}")
            # 비밀번호 암호화
            hashed_password = self.get_password_hash(data.login_password)

            # 입사일(hire_date) 설정 (입력값이 없으므로 오늘 날짜로 설정)
            hire_date = datetime.now().date()

            # DB Insert
            insert_query = text("""
                INSERT INTO employees (
                    employee_id, employee_name, phone_number, job_rank_id, 
                    department_code, home_address, company_email, login_password, 
                    gender_code, birth_date, hire_date, account_creation_date
                ) VALUES (
                    :emp_id, :name, :phone, :rank_id, 
                    :dept_code, :address, :email, :password, 
                    :gender, :birth, :hire_date, CURRENT_DATE
                )
            """)

            params = {
                "emp_id": new_emp_id,
                "name": data.employee_name,
                "phone": data.phone_number,
                "rank_id": data.job_rank_id,
                "dept_code": data.department_code,
                "address": data.home_address,
                "email": data.company_email,
                "password": hashed_password, # 암호화된 비밀번호 저장
                "gender": data.gender_code,
                "birth": data.birth_date,
                "hire_date": hire_date
            }

            await self.session.execute(insert_query, params)
            await self.session.commit()

            return {"employee_id": new_emp_id, "name": data.employee_name}

        except HTTPException as e:
            raise e
        except Exception as e:
            await self.session.rollback()
            print(f"회원가입 에러: {e}")
            raise HTTPException(status_code=500, detail=f"회원가입 처리 중 오류 발생: {str(e)}")
    
    
    # 비밀번호 검증 함수
    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    # 로그인 로직
    async def login_employee(self, data: LoginRequest) -> LoginResponse:
        # 이메일로 사용자 정보 조회 (직접 테이블 조회 대신 SECURITY DEFINER 함수 호출)
        query = text("""
            SELECT employee_id, employee_name, job_rank_id, department_code, company_email, login_password, parent_department_code
            FROM fn_check_login(:p_company_email)
        """)
        
        result = await self.session.execute(query, {"p_company_email": data.company_email})
        member_row = result.fetchone()

        # 사용자 존재 여부 체크
        if not member_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일을 잘못 입력하셨습니다."
            )

        # DB에서 조회된 암호화된 비밀번호
        db_password = member_row.login_password
        
        # 비밀번호 검증 (평문 vs 암호화된 DB값)
        if not self.verify_password(data.login_password, db_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비밀번호가 일치하지 않습니다."
            )

        # 토큰 생성을 위한 데이터 준비
        member_info_dict = {
            "employee_id": member_row.employee_id,
            "employee_name": member_row.employee_name,
            "job_rank_id": member_row.job_rank_id,
            "department_code": member_row.department_code,
            "company_email": member_row.company_email,
            "parent_department_code" : member_row.parent_department_code
        }
        
        # JWT 발급
        access_token = JwtUtils.create_access_token(member_info_dict)
        refresh_token = JwtUtils.create_refresh_token(member_info_dict)

        # 결과 반환 객체 생성
        member_info = MemberInfo(**member_info_dict)
        token_info = TokenInfo(access_token=access_token, refresh_token=refresh_token)

        return LoginResponse(member=member_info, token=token_info)
    
    
    # 토큰 재발급
    async def refresh_access_token(self, refresh_token: str, member_request: MemberInfo) -> dict:
        # 리프레시 토큰 유효성 검증
        decoded_member_info = JwtUtils.validate_token(refresh_token)

        # 보안 강화를 위해, 요청된 회원 정보와 토큰 내 정보 일치 여부 확인
        if decoded_member_info.employee_id != member_request.employee_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰 정보가 일치하지 않습니다."
            )

        # 새로운 Access Token 발급
        member_dict = {
            "employee_id": decoded_member_info.employee_id,
            "employee_name": decoded_member_info.employee_name,
            "job_rank_id": decoded_member_info.job_rank_id,
            "department_code": decoded_member_info.department_code,
            "company_email": decoded_member_info.company_email,
            "parent_department_code" : decoded_member_info.parent_department_code
        }
        
        new_access_token = JwtUtils.create_access_token(member_dict)

        # 프론트엔드 규격(resData)에 맞춰 반환
        return {"access_token": new_access_token}
from typing import TypedDict, List, Optional, Literal, Union, Dict
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import date
from typing import Optional

# LangGraph 스키마
class AgentState(TypedDict):
    question: str
    employee_id: str
    job_rank_id : str             # RLS용 직급 정보
    department_code: str          # RLS용 부서 정보
    parent_department : str       # RLS용 상위부서 정보
    company_email : str           # 사용자 이메일
    file_context: str             # 업로드 파일
    history: List[Dict[str, str]] # 이전 대화 기록
    
    # Router Outputs
    intent: Literal["rdb", "vector", "both"]
    optimized_sql_keywords: List[str]  # Text-to-SQL용 키워드
    optimized_vector_query: str        # Vector Search용 확장 쿼리
    
    # Tool Outputs
    rdb_result: Optional[str]
    vector_result: Optional[str]
    
    # Final Output
    final_answer: str

# 정형/비정형 경로를 위한 Router 스키마
class RouterOutput(BaseModel):
    intent: Literal["rdb", "vector", "both"] = Field(description="데이터 조회 경로 선택")
    sql_keywords: List[str] = Field(description="SQL 생성을 위한 핵심 명사/키워드 리스트")
    vector_query: str = Field(description="유의어가 포함된 자연어 검색 쿼리")

# 채팅 - 사용자 요청 스키마
class ChatRequest(BaseModel):
    query: str                  # 사용자 질문
    employee_id: str            # 사원 ID
    job_rank_id : str           # 직급 ID
    department_code: str        # 부서코드
    parent_department: str      # 상위부서코드
    company_email : str       # 사용자 이메일

# 회원가입 요청 스키마    
class Member(BaseModel):
    employee_name: str
    phone_number: str
    job_rank_id: int
    department_code: str
    home_address: Optional[str] = None
    company_email: EmailStr
    login_password: str
    gender_code: str
    birth_date: date

    # 성별 코드 검증 (M 또는 F만 허용)
    @field_validator('gender_code')
    def validate_gender(cls, v):
        if v not in ('M', 'F'):
            raise ValueError("성별은 'M' 또는 'F'여야 합니다.")
        return v    
    
# 회원가입 응답 스키마
class MemberResponse(BaseModel):
    message: str    
    
# 로그인 요청 스키마    
class LoginRequest(BaseModel):
    company_email: EmailStr
    login_password: str    
    
# 토큰 정보를 담을 스키마
class TokenInfo(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"

# 로그인 성공 시 반환할 회원 정보
class MemberInfo(BaseModel):
    employee_id: str
    employee_name: str
    job_rank_id: int
    department_code: str
    company_email: EmailStr
    parent_department_code : str

# 최종 로그인 응답 (회원정보 + 토큰)
class LoginResponse(BaseModel):
    member: MemberInfo
    token: TokenInfo    
    
    
# 공지사항 목록 조회 응답
class AnnouncementListResponse(BaseModel):
    announcement_id: int
    title: str
    department_name: str
    created_at: date | object

#  공지사항 작성 요청
class AnnouncementCreateRequest(BaseModel):
    title: str
    content: str
    parent_department_code: str # DB 컬럼은 parent_department
    employee_id: str
    job_rank_id:str

# 공지사항 상세 조회 응답
class AnnouncementDetailResponse(BaseModel):
    announcement_id: int
    title: str
    content: str
    parent_department_code: str
    department_name: str
    employee_id: str
    employee_name: str
    created_at: date | object
    updated_at: Optional[date | object] = None

# 메일 전송 요청
class MailSendRequest(BaseModel):
    receiver_email: EmailStr
    sender_email: EmailStr
    subject: str
    content: str

# 보낸 메일함 목록 조회 응답
class MailListResponse(BaseModel):
    mail_id: int
    receiver_email: str
    subject: str
    content: str
    sent_at: date | object

# 주소록 목록 조회 응답
class AddressBookResponse(BaseModel):
    employee_name: str
    company_email: str
    home_address: Optional[str]
    phone_number: str
    department_name: str
    job_rank_name: str    
    
# 회의실 예약 요청
class ReservationCreateRequest(BaseModel):
    department_code: str
    employee_id: str
    meeting_room_id: str
    usage_date: date
    start_time: int

    @field_validator('start_time')
    def validate_time(cls, v):
        if not (0 <= v <= 23):
            raise ValueError("시간은 0~23 사이의 정수여야 합니다.")
        return v
# 회의실 예약 취소 요청    
class ReservationCancelRequest(BaseModel):
    reservation_id_list: List[int]
    employee_id: str    

# 일별 예약 현황 응답 ("YYYY-MM-DD": bool)
# Key가 날짜 스트링이므로 Dict[str, bool] 사용
MonthlyReservationResponse = dict[str, bool]

# 시간별 예약 현황 응답 
# 예시: {"8": True, "department_name": "인사팀"}
DailyReservationResponseItem = dict[str, Union[bool, Optional[str]]]    
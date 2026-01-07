import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

import json
import time
import redis
import shutil
from typing import List
from datetime import date
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, Depends, status, Form, File, UploadFile, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from faster_whisper import WhisperModel

from app.graph.workflow import app_graph
from app.core.semantic_cache import SemanticCacheManager
from app.core.dependencies import check_access_token
from app.core.database import get_db
from app.utils.file_parser import parse_uploaded_file
from app.services.member import MemberService
from app.services import announcement_service, mail_service, meeting_service 
from app.services.memory import ConversationMemoryManager
from app.schemas.model import (
    Member, MemberResponse, LoginRequest, LoginResponse, MemberInfo, ChatRequest,
    AnnouncementListResponse, AnnouncementCreateRequest, AnnouncementDetailResponse,
    MailSendRequest, MailListResponse, AddressBookResponse, MonthlyReservationResponse,
    DailyReservationResponseItem, ReservationCreateRequest, ReservationCancelRequest
)

# Redis 클라이언트 초기화 및 캐시, 메모리 공유
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=False)

# Redis 설정 및 Semantic Cache 매니저 초기화
semantic_cache: SemanticCacheManager = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 초기화
    global semantic_cache
    semantic_cache = SemanticCacheManager(redis_client)
    yield

# 이전 대화 기록을 위한 메모리 버퍼 설정    
memory_manager = ConversationMemoryManager(redis_client, window_size=30)    
    
# 앱으로 들어오는 모든 요청에 대해, check_access_token을 실행하여 accessToken 검증
app = FastAPI(lifespan=lifespan, dependencies=[Depends(check_access_token)], title="Deep Nexus AI Backend")  

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 핵심: 모든 메서드(OPTIONS 포함) 허용
    allow_headers=["*"],  # 핵심: 모든 헤더 허용
)


@app.post("/signup", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: Member, db: AsyncSession = Depends(get_db)):
    """
    회원가입
    """
    member_service = MemberService(db)
    result = await member_service.create_employee(request)
    
    return MemberResponse(
        message="회원가입이 성공적으로 완료되었습니다."
    )
    
@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    이메일 로그인
    """
    member_service = MemberService(db)
    return await member_service.login_employee(request)    


@app.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(
    member_request: MemberInfo,                         # Body : 재발급에 필요한 회원 정보
    refresh_token: str = Header(alias="refreshToken"),  # Header: 리프레시 토큰
    db: AsyncSession = Depends(get_db)
):
    """
    AccessToken 재발급
    """
    member_service = MemberService(db)
    
    # 토큰 재발급 처리
    return await member_service.refresh_access_token(refresh_token, member_request)


# 비동기 처리하여, I/O(DB, LLM, Redis)작업 시, 서버가 블로킹 되지 않도록 함.
@app.post("/chat")
async def chat_endpoint(
    file: UploadFile = File(None), # 업롣 ㅡ파일
    request_data: str = Form(...), # 채팅 시, 요청한 파라미터
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    start_time = time.perf_counter()
    
    # 사용자 업로드 파일 처리
    try:
        data_dict = json.loads(request_data)
        request = ChatRequest(**data_dict)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON format: {str(e)}")
    
    file_context_str = ""
    if file:
        print(f"📁 파일 처리 시작: {file.filename}")
        file_context_str = await parse_uploaded_file(file)
        print(f"📄 추출된 내용: {file_context_str[:100]}...")
    
    # Redis 캐시 정보 확인     
    cached_response = await semantic_cache.search_cache(request.query)
    
    if cached_response:
        # 캐시 히트 시: 저장된 텍스트를 스트리밍 형식으로 반환
        async def cached_stream_generator():
            print(f"\n [Semantic Cache Hit] > ", end="", flush=True)
            yield cached_response

        return StreamingResponse(cached_stream_generator(), media_type="text/event-stream")

    # Redis Memory 버퍼 에서, 이전 대화 내용 읽어오기 
    history = await memory_manager.get_history(request.employee_id)
    
    # Graph Execution & Streaming
    async def event_generator():
        final_output = ""
        is_first_chunk = True
        
        # LangGraph astream_events 사용하여 토큰 단위 스트리밍
        inputs = {
            "question": request.query,
            "employee_id": request.employee_id,
            "job_rank_id" : request.job_rank_id,
            "department_code": request.department_code,
            "parent_department" : request.parent_department,
            "company_email" : request.company_email,
            "file_context": file_context_str,
            "history" : history
        }
        
        # app.graph.workflow - LangGraph 실행
        async for event in app_graph.astream_events(inputs, version="v1"):
            kind = event["event"]
            node_name = event["metadata"].get("langgraph_node", "Unknown")
            
            print(f"event : {event}")
            # ------------------------------------------------------------------
            # 1. [디버깅] 노드 진입/완료 확인 (Router -> SQL Agent -> ...)
            # ------------------------------------------------------------------
            if kind == "on_chain_start" and node_name in ["router", "sql_agent", "vector_search", "generator"]:
                print(f"  🔄 [Node Start] {node_name} 노드 진입...")
                
            elif kind == "on_chain_end" and node_name in ["router", "sql_agent", "vector_search"]:
                # 각 노드가 뱉어낸 결과값(Output) 확인
                output_data = event["data"].get("output")
                if output_data:
                    # 결과가 너무 길면 앞부분만 출력
                    print(f"  ✅ [Node End] {node_name} 완료. 결과: {str(output_data)[:100]}...")

            # ------------------------------------------------------------------
            # 2. [디버깅] Router의 판단 결과 확인
            # ------------------------------------------------------------------
            if kind == "on_chain_end" and node_name == "router":
                router_output = event["data"]["output"]
                print(f"     👉 Router 판단: {router_output})")

            # ------------------------------------------------------------------
            # 3. [디버깅] 툴 실행 결과 확인 (SQL 쿼리 결과, 검색된 문서 등)
            # ------------------------------------------------------------------
            if kind == "on_tool_end":
                tool_name = event["name"]
                tool_output = event["data"].get("output")
                print(f"     🛠️ [Tool] {tool_name} 실행 완료.")
                # SQL 쿼리 결과나 검색된 문서 내용 미리보기
                print(f"        결과: {str(tool_output)[:150]}...")
            
            # ------------------------------------------------------------------
            # 4. [클라이언트 전송] 최종 답변 스트리밍 (기존 로직)
            # ------------------------------------------------------------------
            if kind == "on_chat_model_stream" and node_name == "generator":
                content = event["data"]["chunk"].content
                if content:
                    if is_first_chunk:
                        print(f"\n 💬 [Streaming Start] >> ", end="", flush=True)
                        is_first_chunk = False
                    
                    # 1. 터미널 로그에 실시간 출력 (줄바꿈 없이)
                    print(content, end="", flush=True)
                    
                    # 2. 데이터 누적
                    final_output += content
                    
                    # 3. 프론트엔드로 전송
                    yield content
                    
        end_time = time.perf_counter()
        total_duration = end_time - start_time            
        
        if not is_first_chunk:
            print("\n ✅ [Streaming End] : Total Runtime {:.2f} seconds".format(total_duration))
            
        # Redis 캐시 저장(만료 시간 1시간) 및 메모리에 대화 내용 기록
        if final_output:
            background_tasks.add_task(
                semantic_cache.store_cache, 
                query_text=request.query, 
                response_text=final_output
            )
            background_tasks.add_task(
                memory_manager.add_message, 
                session_id=request.employee_id, 
                role="user", 
                content=request.query
            )
            background_tasks.add_task(
                memory_manager.add_message, 
                session_id=request.employee_id, 
                role="assistant", 
                content=final_output
            )

    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/announcements", response_model=List[AnnouncementListResponse])
async def read_announcements(
    parent_department_code: str = Query(..., description="상위 부서 코드"),
    employee_id: str = Query(..., description="사원 ID"),
    db: AsyncSession = Depends(get_db)
):
    """공지사항 목록 조회"""
    return await announcement_service.get_announcement_list(db, parent_department_code, employee_id)
@app.post("/announcements")
async def create_announcement_item(
    request: AnnouncementCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """공지사항 작성 요청"""
    return await announcement_service.create_announcement(db, request)

@app.get("/announcements/{announcement_id}", response_model=AnnouncementDetailResponse)
async def read_announcement_detail(
    announcement_id: int,
    employee_id: str,
    db: AsyncSession = Depends(get_db)
):
    """공지사항 상세보기 요청"""
    return await announcement_service.get_announcement_detail(db, announcement_id, employee_id)
@app.post("/mails/send")
async def send_mail(
    request: MailSendRequest,
    db: AsyncSession = Depends(get_db)
):
    """메일 전송"""
    return await mail_service.send_email_logic(db, request)

@app.get("/mails/sent", response_model=List[MailListResponse])
async def read_sent_mails(
    sender_email: str = Query(..., description="발신자 이메일"),
    db: AsyncSession = Depends(get_db)
):
    """보낸 메일함 목록 조회"""
    return await mail_service.get_sent_mails(db, sender_email)

@app.delete("/mails/{mail_id}")
async def delete_sent_mails(
    mail_id: int,
    sender_email: str = Query(..., description="발신자 이메일"),
    db: AsyncSession = Depends(get_db)
):
    """보낸 메일함 삭제"""
    return await mail_service.delete_sent_mails(db, mail_id, sender_email)

@app.get("/address-book", response_model=List[AddressBookResponse])
async def read_address_book(
    db: AsyncSession = Depends(get_db)
):
    """주소록 목록 조회"""
    return await mail_service.get_address_book(db)


@app.get("/meeting-rooms/reservations/monthly", response_model=MonthlyReservationResponse)
async def get_monthly_reservations(
    meeting_room_id: str = Query(..., description="미팅룸 ID"),
    year_month: str = Query(..., description="조회 월 (YYYY-MM)"),
    employee_id:str=Query(..., description="사원 ID"),
    db: AsyncSession = Depends(get_db)
):
    """일별 예약 현황 조회"""
    return await meeting_service.get_monthly_status(db, meeting_room_id, year_month, employee_id)

@app.get("/meeting-rooms/reservations/daily", response_model=List[DailyReservationResponseItem])
async def get_daily_reservations(
    meeting_room_id: str = Query(..., description="미팅룸 ID"),
    usage_date: date = Query(..., description="조회 일자 (YYYY-MM-DD)"),
    employee_id:str=Query(..., description="사원 ID"),
    db: AsyncSession = Depends(get_db)
):
    """일, 시간별 예약 현황 조회"""
    return await meeting_service.get_daily_status(db, meeting_room_id, usage_date, employee_id)

@app.post("/meeting-rooms/reservations")
async def create_reservation(
    request: ReservationCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """회의실 예약 요청"""
    print("TEST")
    return await meeting_service.create_reservation(db, request)

@app.delete("/meeting-rooms/reservations")
async def delete_reservation(
    request: ReservationCancelRequest,
    db: AsyncSession = Depends(get_db)
):
    """회의실 예약 취소 요청"""
    return await meeting_service.delete_reservation(db, request.reservation_id_list, request.employee_id)




# 모델 크기 옵션: "tiny", "base", "small", "medium", "large-v3"
# device="cuda" (GPU 사용 시), device="cpu" (CPU 사용 시)
# compute_type="float16" (GPU), compute_type="int8" (CPU)
MODEL_SIZE = "medium" 
try:
    # GPU가 있으면 GPU로, 없으면 CPU로 설정하는 로직 (원하는 대로 고정해도 됨)
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
except ImportError:
    device = "cpu"
    compute_type = "int8"

print(f"Loading Faster Whisper model '{MODEL_SIZE}' on {device} with {compute_type}...")
model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute_type)
print("Model loaded successfully.")

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """
    클라이언트로부터 오디오 파일을 받아 Faster-Whisper로 변환하여 반환
    """
    
    # 임시 파일 경로 생성
    temp_filename = f"temp_{file.filename}"
    
    try:
        # 3. 업로드된 파일을 로컬 임시 파일로 저장
        # faster-whisper는 파일 경로를 입력받는 것이 가장 안정적입니다.
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 4. Transcribe (변환) 수행
        # segments는 제너레이터이므로 리스트로 변환하거나 반복문으로 텍스트 추출
        segments, info = model.transcribe(temp_filename, beam_size=5, language="ko", vad_filter=True, temperature=0.0, condition_on_previous_text=False)
        
        # 5. 결과 텍스트 합치기
        result_text = "".join([segment.text for segment in segments]).strip()
        
        print(f"Detected language: {info.language}, Probability: {info.language_probability}")
        print(f"Transcription: {result_text}")

        return {"transcript": result_text}

    except Exception as e:
        print(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=f"STT processing failed: {str(e)}")
        
    finally:
        # 6. 임시 파일 삭제 (클린업)
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
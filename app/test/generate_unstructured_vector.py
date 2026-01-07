import docx2txt
import os
import io
import asyncio
import chardet
import numpy as np
import pandas as pd
import nltk
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

# Google API 관련
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# DB 관련 (SQLAlchemy + pgvector)
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, func, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from pgvector.sqlalchemy import Vector

# [추가] LangChain 관련 라이브러리 임포트
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

# 현재 실행 중인 스크립트 파일의 디렉토리 경로를 가져옵니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------
# [설정 구역] 환경에 맞게 수정하세요
# ---------------------------------------------------------
DATABASE_URL = "postgresql+asyncpg://deepnexus:team6%21%40%23%24@deepnexus-db.postgres.database.azure.com:5432/postgres"
EMBEDDING_MODEL_NAME = 'nlpai-lab/KURE-v1'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'deepnexus_client.json')
VECTOR_DIMENSION = 1024 

# NLTK 데이터 다운로드
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

# SQLAlchemy 베이스 모델
Base = declarative_base()

class DeepNexusDoc(Base):
    __tablename__ = 'tbl_deep_nexus_docs'
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(255))
    chunk_index = Column(Integer)
    doc_title = Column(String(500))
    doc_url = Column(Text)
    content = Column(Text, nullable=False)
    content_vector = Column(Vector(VECTOR_DIMENSION))
    metadata_info = Column("metadata", JSON)
    permission_list = Column(JSON)
    version = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# 구글 드라이브 API 서비스 객체 생성
def get_drive_service():
    """Google Drive API 서비스 객체 생성"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

# 메인 함수
async def process_and_ingest():
    # 1. 초기화
    print(f" >> 모델 로드 중: {EMBEDDING_MODEL_NAME}")
    
    # [변경] LangChain용 임베딩 객체 생성 (청킹용)
    # 청킹 단계에서 유사도를 계산하기 위해 LangChain 래퍼가 필요합니다.
    hf_embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    
    # [변경] LangChain SemanticChunker 초기화
    semantic_splitter = SemanticChunker(
        hf_embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=90
    )

    # 기존 벡터 생성용 모델 (DB 저장용 실제 벡터 추출을 위해 유지)
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    service = get_drive_service()
    
    # 2. 파일 리스트 조회
    print(" >> Google Drive 스캔 중...")
    query = "mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    fields = "files(id, name, mimeType, webViewLink, modifiedTime, version)"
    
    results = service.files().list(q=query, fields=fields).execute()
    items = results.get('files', [])

    if not items:
        print(" !! 처리할 파일이 없습니다.")
        return

    # 3. 파일별 처리 루프
    async with AsyncSessionLocal() as session:
        print(f" >> 총 {len(items)}개의 파일 검사 시작!")
        
        for item in items:
            f_id = item['id']
            name = item['name']
            mime = item['mimeType']
            
            drive_version = str(item.get('version', '0'))
            drive_modified = item.get('modifiedTime')
            
            # 텍스트 파일만 처리하도록 필터링 (필요시 pdf 등 추가)
            if not any(ext in mime for ext in ['text/plain', 'pdf', 'document']):
                continue

            # DB 체크 로직
            stmt = select(DeepNexusDoc).where(DeepNexusDoc.file_id == f_id).limit(1)
            result = await session.execute(stmt)
            existing_doc = result.scalars().first()

            needs_update = False
            is_new_file = False

            if not existing_doc:
                is_new_file = True
                print(f"\n[NEW] 신규 파일 발견: {name}, {mime}")
            else:
                db_version = existing_doc.version
                db_modified = existing_doc.metadata_info.get('modified_time')

                if drive_version != db_version or drive_modified != db_modified:
                    needs_update = True
                    print(f"\n[UPDATE] 변경 감지: {name} (Ver: {db_version}->{drive_version})")
                else:
                    print(f"[SKIP] 변경 없음: {name}")
                    continue

            try:
                content = ""
                
                # 1. Google Workspace 문서 전용 처리 (Drive 자체 포맷)
                if 'application/vnd.google-apps.document' in mime: # Google Docs
                    content = service.files().export_media(fileId=f_id, mimeType='text/plain').execute().decode('utf-8')
                elif 'application/vnd.google-apps.spreadsheet' in mime: # Google Sheets
                    content = service.files().export_media(fileId=f_id, mimeType='text/csv').execute().decode('utf-8')
                
                # 2. 일반 업로드 파일 처리 (Binary 다운로드)
                else:
                    request = service.files().get_media(fileId=f_id)
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done: _, done = downloader.next_chunk()
                    file_bytes = fh.getvalue()

                    # [중요] 한글 인코딩 자동 감지 함수
                    def safe_decode(data):
                        try:
                            return data.decode('utf-8')
                        except UnicodeDecodeError:
                            # utf-8 실패 시 인코딩 감지 시도 (cp949 등)
                            detected = chardet.detect(data)['encoding']
                            return data.decode(detected if detected else 'cp949', errors='replace')

                    # PDF 처리 (PyMuPDF는 기본적으로 유니코드를 지원하지만 폰트에 따라 다를 수 있음)
                    if 'pdf' in mime:
                        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                            # 텍스트 추출 시 유니코드 옵션 확인
                            content = "".join([page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for page in doc])
                    
                    # Excel 처리
                    elif 'spreadsheetml.sheet' in mime or 'excel' in mime or name.endswith(('.xlsx', '.xls')):
                        # 엑셀은 내부적으로 XML 기반(UTF-8)이라 보통 안전하지만, 엔진을 명시합니다.
                        df_dict = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, engine='openpyxl')
                        content = "\n\n".join([f"[시트: {s}]\n{df.to_string(index=False)}" for s, df in df_dict.items()])
                    
                    # Word 처리 (python-docx는 유니코드 기반이라 안전)
                    elif 'wordprocessingml.document' in mime or name.endswith('.docx'):
                        print(f" >> [{name}] docx2txt를 이용한 전수 추출 시작...")
                        try:
                            # 방법 1: 바이너리 데이터를 직접 docx2txt로 전달 (가장 확실함)
                            doc_stream = io.BytesIO(file_bytes)
                            content = docx2txt.process(doc_stream)
                            
                            # [검증] 추출 직후 한글 포함 여부 체크
                            import re
                            korean_text = re.findall(r'[가-힣]+', content)
                            
                            if not korean_text:
                                print(f" !! [경고] 여전히 한글이 없습니다. Google Docs Export로 재시도합니다.")
                                # 방법 2: Google API 자체 변환 기능으로 Fallback
                                content = service.files().export_media(fileId=f_id, mimeType='text/plain').execute().decode('utf-8-sig')
                            else:
                                print(f" >> [성공] 한글 단어 {len(korean_text)}개 추출 완료.")
                                
                        except Exception as e:
                            print(f" !! docx2txt 처리 중 오류 발생: {e}")
                            content = ""

                        # [최종 확인] 추출된 content에 한글이 있는지 다시 확인
                        import re
                        korean_check = re.findall(r'[가-힣]+', content)
                        if not korean_check:
                            print(f" !! [위험] {name}: 추출 후에도 한글이 발견되지 않음. (글자가 이미지 형태일 가능성)")
                        else:
                            print(f" >> [성공] {name}: 한글 데이터 추출됨. ({len(korean_check)}개 단어)")

                    # 일반 텍스트 파일 (여기서 한글 누락이 가장 많음)
                    elif 'text/plain' in mime or name.endswith('.txt'):
                        content = safe_decode(file_bytes)
                    
                    # JSON 파일
                    elif 'json' in mime:
                        content = safe_decode(file_bytes)

                if not content.strip(): 
                    print(f" >> [{name}] 빈 내용이거나 추출할 수 없는 형식입니다.")
                    continue

                # B. 기존 데이터 삭제
                if needs_update:
                    await session.execute(delete(DeepNexusDoc).where(DeepNexusDoc.file_id == f_id))
                    print(f" >> 기존 데이터 삭제 완료 ({name})")

                # C. [변경] LangChain SemanticChunker 사용
                # 문서를 청킹하여 LangChain Document 객체 리스트로 반환
                lc_docs = semantic_splitter.create_documents([content])
                chunks = [doc.page_content for doc in lc_docs]
                
                print(f" >> [시맨틱 청킹] {len(chunks)}개 생성 완료")

                # 벡터 생성 (DB 저장을 위해 기존 방식 유지)
                vectors = model.encode(chunks)
                
                # D. DB 객체 생성
                db_objs = []
                for idx, (chunk_text, vec) in enumerate(zip(chunks, vectors)):
                    final_vec = vec.tolist()
                    if len(final_vec) < VECTOR_DIMENSION:
                        final_vec += [0.0] * (VECTOR_DIMENSION - len(final_vec))

                    db_objs.append(DeepNexusDoc(
                        file_id=f_id,
                        chunk_index=idx,
                        doc_title=name,
                        doc_url=item.get('webViewLink'),
                        content=chunk_text,
                        content_vector=final_vec,
                        version=drive_version,
                        metadata_info={
                            "modified_time": drive_modified,
                            "source": "drive_sync"
                        },
                        permission_list={"role": "admin"}
                    ))

                session.add_all(db_objs)
                await session.commit()
                
                action_str = "신규 저장" if is_new_file else "업데이트 완료"
                print(f" >> {action_str}: {len(db_objs)}개 청크.")
                
            except Exception as e:
                print(f" !! 오류 발생 ({name}): {e}")
                await session.rollback()

    print("\n[✔] 모든 비정형 데이터 작업이 완료되었습니다.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(process_and_ingest())
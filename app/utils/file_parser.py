# app/utils/file_parser.py
import io
from fastapi import UploadFile
from pypdf import PdfReader

async def parse_uploaded_file(file: UploadFile) -> str:
    """
    업로드된 파일을 읽어 텍스트로 반환합니다.
    """
    filename = file.filename.lower()
    content = await file.read()
    
    extracted_text = ""

    # 1. PDF 파일 처리
    if filename.endswith(".pdf"):
        try:
            pdf_reader = PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                extracted_text += page.extract_text() + "\n"
        except Exception as e:
            return f"[파일 읽기 오류: {str(e)}]"

    # 2. 텍스트/코드/CSV 파일 처리
    elif filename.endswith((".txt", ".csv", ".py", ".md", ".json", ".log")):
        try:
            extracted_text = content.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = content.decode("cp949", errors="ignore") # 한글 인코딩 예외 처리

    # 3. 그 외 (이미지 등은 OCR이나 멀티모달 처리가 필요하지만 여기선 생략)
    else:
        return "[지원하지 않는 파일 형식입니다. 텍스트나 PDF만 가능합니다.]"

    # 파일 내용을 LLM이 이해하기 쉽게 포맷팅
    return f"\n\n=== [첨부 파일 내용: {file.filename}] ===\n{extracted_text}\n=====================================\n"
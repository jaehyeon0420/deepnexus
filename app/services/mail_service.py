from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.orm import SendMail, Employee, Department, JobRank
from app.schemas.model import MailSendRequest, MailListResponse, AddressBookResponse
from app.core.config import settings
from fastapi import HTTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

# 메일 전송 및 DB 저장
async def send_email_logic(db: AsyncSession, req: MailSendRequest):
    await db.execute(
            text("""SELECT set_config('app.current_email', :sender_email, true) """),
            {"sender_email": req.sender_email}
        )
    
    # 메일 발송 (Naver SMTP)
    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_USER
    msg['To'] = req.receiver_email
    msg['Subject'] = req.subject
    msg.attach(MIMEText(req.content, 'plain', 'utf-8'))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_SERVER,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메일 전송 실패: {str(e)}")

    # DB 저장
    new_mail = SendMail(
        receiver_email=req.receiver_email,
        sender_email=req.sender_email,
        subject=req.subject,
        content=req.content
    )
    db.add(new_mail)
    await db.commit()
    
    return {"message": "메일 전송 및 저장이 완료되었습니다."}

# 보낸 메일함 목록 조회
async def get_sent_mails(db: AsyncSession, sender_email: str):
    await db.execute(
            text("""SELECT set_config('app.current_email', :sender_email, true) """),
            {"sender_email": sender_email}
        )
    
    query = (
        select(SendMail)
        .where(SendMail.sender_email == sender_email)
        .order_by(desc(SendMail.sent_at))
    )
    result = await db.execute(query)
    mails = result.scalars().all()
    
    # sender_email 제외하고 반환
    return [
        MailListResponse(
            mail_id=mail.mail_id,
            receiver_email=mail.receiver_email,
            subject=mail.subject,
            content=mail.content,
            sent_at=mail.sent_at
        ) for mail in mails
    ]
# 보낸 메일함 삭제
async def delete_sent_mails(db: AsyncSession, mail_id: int, sender_email: str):
    await db.execute(
            text("""SELECT set_config('app.current_email', :sender_email, true) """),
            {"sender_email": sender_email}
        )
    
    query = (
        select(SendMail)
        .where(
            SendMail.mail_id == mail_id,
            SendMail.sender_email == sender_email
        )
    )
    result = await db.execute(query)
    mail = result.scalar_one_or_none()
    
    if not mail:
        raise HTTPException(status_code=404, detail="해당 메일을 찾을 수 없습니다.")
    
    await db.delete(mail)
    await db.commit()
    
    return {"message": "보낸 메일함에서 메일이 삭제되었습니다."}

# 주소록 목록 조회
from sqlalchemy import text
async def get_address_book(db: AsyncSession):
    # 1. RLS를 우회하는 SECURITY DEFINER 함수 호출 정의
    # SELECT * 를 사용하면 함수에서 정의한 모든 컬럼(6개)을 가져옵니다.
    query = text("SELECT * FROM fn_get_full_address_book()")
    
    # 2. 쿼리 실행
    result = await db.execute(query)
    
    # 3. 모든 결과 로우 가져오기
    # SQLAlchemy 2.0 스타일에서는 fetchall() 또는 result.all()을 사용합니다.
    rows = result.fetchall()
    
    # 4. Pydantic 모델(AddressBookResponse)로 매핑하여 반환
    return [
        AddressBookResponse(
            employee_name=row.employee_name,
            company_email=row.company_email,
            home_address=row.home_address,
            phone_number=row.phone_number,
            department_name=row.department_name,
            job_rank_name=row.job_rank_name
        ) for row in rows
    ]
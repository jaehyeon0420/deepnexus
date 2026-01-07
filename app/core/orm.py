from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, func, Date
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# 부서 테이블 (Join용 가상 정의)
class Department(Base):
    __tablename__ = "departments"
    department_code = Column(String(10), primary_key=True)
    department_name = Column(String(100))

# 직급 테이블 (Join용 가상 정의)
class JobRank(Base):
    __tablename__ = "job_ranks"
    job_rank_id = Column(Integer, primary_key=True)
    job_rank_name = Column(String(50))

# 사원 테이블
class Employee(Base):
    __tablename__ = "employees"
    employee_id = Column(String(20), primary_key=True)
    employee_name = Column(String(50))
    department_code = Column(String(10), ForeignKey("departments.department_code"))
    job_rank_id = Column(Integer, ForeignKey("job_ranks.job_rank_id"))
    company_email = Column(String(100))
    home_address = Column(String(200))
    phone_number = Column(String(20))

    department = relationship("Department")
    job_rank = relationship("JobRank")

# 공지사항 테이블
class Announcement(Base):
    __tablename__ = "announcement"
    
    announcement_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    parent_department_code = Column(String(10), ForeignKey("departments.department_code")) # 컬럼명 parent_department
    employee_id = Column(String(20), ForeignKey("employees.employee_id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    department = relationship("Department")
    employee = relationship("Employee")

# 보낸 메일함 테이블
class SendMail(Base):
    __tablename__ = "send_mail"

    mail_id = Column(Integer, primary_key=True, autoincrement=True)
    receiver_email = Column(String(100), nullable=False)
    sender_email = Column(String(100), nullable=False)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=func.now())
    
# 회의실 마스터
class MeetingRoom(Base):
    __tablename__ = "meeting_room"
    
    meeting_room_id = Column(String(10), primary_key=True)
    room_name = Column(String(10))

# 회의실 예약 내역
class ReservationMeetingRoom(Base):
    __tablename__ = "reservation_meeting_room"

    reservation_id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_room_id = Column(String(10), ForeignKey("meeting_room.meeting_room_id"))
    employee_id = Column(String(20), ForeignKey("employees.employee_id"))
    department_code = Column(String(10), ForeignKey("departments.department_code"))
    usage_date = Column(Date, nullable=False)
    start_time = Column(Integer, nullable=False) # 예: 8, 9, 10 ...
    reserved_at = Column(DateTime, default=func.now())

    # Relationships
    meeting_room = relationship("MeetingRoom")
    employee = relationship("Employee")
    department = relationship("Department")    
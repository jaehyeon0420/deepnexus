from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from app.core.orm import ReservationMeetingRoom, Department
from app.schemas.model import ReservationCreateRequest
from fastapi import HTTPException
from datetime import date, timedelta
import calendar


# 운영 시간 정의
OPERATING_HOURS = range(8, 24, 2)

# 일별 예약 현황 조회
async def get_monthly_status(db: AsyncSession, meeting_room_id: str, year_month: str, employee_id: str):
    await db.execute(
            text("""SELECT set_config('app.current_employee_id', :emp_id, true) """),
            {"emp_id": employee_id}
        )
    
    try:
        year, month = map(int, year_month.split('-'))
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식은 YYYY-MM 이어야 합니다.")

    # 해당 월의 시작일과 마지막 날짜 구하기
    _, last_day = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    # DB 조회: 해당 기간, 해당 룸의 예약된 날짜만 가져오기 (Distinct)
    query = (
        select(ReservationMeetingRoom.usage_date)
        .where(
            and_(
                ReservationMeetingRoom.meeting_room_id == meeting_room_id,
                ReservationMeetingRoom.usage_date.between(start_date, end_date)
            )
        )
        .distinct()
    )
    result = await db.execute(query)
    reserved_dates = {row.usage_date for row in result.all()} # Set으로 변환하여 검색 속도 향상

    # 전체 일자 생성 및 True/False 매핑
    response = {}
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        response[date_str] = current_date in reserved_dates
        current_date += timedelta(days=1)

    return response

# 일, 시간별 예약 현황 조회
async def get_daily_status(db: AsyncSession, meeting_room_id: str, usage_date: date, employee_id: str):
    await db.execute(
            text("""SELECT set_config('app.current_employee_id', :emp_id, true) """),
            {"emp_id": employee_id}
        )
    
    # DB 조회: 해당 일자, 해당 룸의 예약 정보 + 부서명 Join
    query = (
        select(ReservationMeetingRoom.start_time, Department.department_name)
        .join(Department, ReservationMeetingRoom.department_code == Department.department_code)
        .where(
            and_(
                ReservationMeetingRoom.meeting_room_id == meeting_room_id,
                ReservationMeetingRoom.usage_date == usage_date
            )
        )
    )
    result = await db.execute(query)
    
    # DB 결과를 Dictionary로 변환 {시간: 부서명}
    reservations = {row.start_time: row.department_name for row in result.all()}

    response_list = []
    
    # 정의된 운영 시간(혹은 0~23)을 순회하며 데이터 생성
    for hour in OPERATING_HOURS:
        str_hour = str(hour)
        is_reserved = hour in reservations
        dept_name = reservations[hour] if is_reserved else None
        
        item = {
            str_hour: is_reserved,
            "department_name": dept_name
        }
        response_list.append(item)

    return response_list

# 회의실 예약 요청
async def create_reservation(db: AsyncSession, req: ReservationCreateRequest):
    await db.execute(
        text("""SELECT set_config('app.current_employee_id', :emp_id, true) """),
        {"emp_id": req.employee_id}
    )
    
    # 1. 중복 예약 체크
    query = select(ReservationMeetingRoom).where(
        and_(
            ReservationMeetingRoom.meeting_room_id == req.meeting_room_id,
            ReservationMeetingRoom.usage_date == req.usage_date,
            ReservationMeetingRoom.start_time == req.start_time
        )
    )
    result = await db.execute(query)
    if result.first():
        raise HTTPException(status_code=409, detail="해당 시간에 이미 예약이 존재합니다.")

    # 2. INSERT 시, 사용되는 reservation_id를 reservation_meeting_room_reservation_id_seq 사용하여 조회하기
    query = text("SELECT nextval('reservation_meeting_room_reservation_id_seq')")
    result = await db.execute(query)
    reservation_id = result.scalar()

    # 3. 예약 정보 저장
    new_reservation = ReservationMeetingRoom(
        reservation_id=reservation_id,
        meeting_room_id=req.meeting_room_id,
        employee_id=req.employee_id,
        department_code=req.department_code,
        usage_date=req.usage_date,
        start_time=req.start_time
    )
    
    db.add(new_reservation)
    await db.commit()
    
    return {"message": "회의실 예약이 완료되었습니다.", "reservation_id": reservation_id}

# 회의실 예약 취소 요청
async def delete_reservation(db: AsyncSession, reservation_id_list: List[int], employee_id: str):
    # 1. (선택사항) RLS 등을 위한 컨텍스트 설정
    await db.execute(
        text("""SELECT set_config('app.current_employee_id', :emp_id, true) """),
        {"emp_id": employee_id}
    )
    
    # 2. [수정] Pydantic 모델이 아닌 ORM 모델(Reservation)을 사용해야 함
    #    [수정] 리스트 비교는 == 가 아니라 .in_()을 사용해야 함
    stmt = select(ReservationMeetingRoom).where(
        ReservationMeetingRoom.reservation_id.in_(reservation_id_list),
        ReservationMeetingRoom.employee_id == employee_id
    )
    
    result = await db.execute(stmt)
    reservations = result.scalars().all() # 조회된 예약 객체 리스트

    # 3. 예외 처리: 삭제할 데이터가 없는 경우
    if not reservations:
        return {"message": "삭제할 예약이 존재하지 않거나 권한이 없습니다."}

    # 4. 조회된 예약들 삭제
    for reservation in reservations:
        await db.delete(reservation)
        
    await db.commit()
    
    return {"message": "예약 취소가 완료되었습니다.", "deleted_count": len(reservations)}
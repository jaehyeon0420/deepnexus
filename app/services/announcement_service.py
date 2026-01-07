from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.orm import Announcement, Department, Employee
from app.schemas.model import AnnouncementCreateRequest, AnnouncementListResponse, AnnouncementDetailResponse
from fastapi import HTTPException
from sqlalchemy import select, desc, text

# 공지사항 목록 조회
async def get_announcement_list(db: AsyncSession, parent_department_code: str, employee_id: str):
    await db.execute(
        text("SELECT set_config('app.current_employee_id', :emp_id, true)"),
        {"emp_id": employee_id}
    )
    
    query = (
        select(
            Announcement.announcement_id,
            Announcement.title,
            Announcement.created_at,
            Department.department_name
        )
        .join(Department, Announcement.parent_department_code == Department.department_code)
        .where(Announcement.parent_department_code == parent_department_code)
        .order_by(desc(Announcement.created_at))
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    return [
        AnnouncementListResponse(
            announcement_id=row.announcement_id,
            title=row.title,
            department_name=row.department_name,
            created_at=row.created_at
        ) for row in rows
    ]

# 공지사항 작성 요청
async def create_announcement(db: AsyncSession, req: AnnouncementCreateRequest):
    async with db.begin():
        await db.execute(
            text("""SELECT set_config('app.current_parent_dept_code', :parent_department_code, true),
                           set_config('app.current_rank_level', :job_rank_id, true),
                           set_config('app.current_employee_id', :emp_id, true)
                """),
            {"parent_department_code": req.parent_department_code, "job_rank_id" : str(req.job_rank_id), "emp_id": req.employee_id}
        )
        
        new_announcement = Announcement(
            title=req.title,
            content=req.content,
            parent_department_code=req.parent_department_code,
            employee_id=req.employee_id
        )
        db.add(new_announcement)

        await db.flush()
        await db.refresh(new_announcement)
    return {"message": "공지사항이 등록되었습니다.", "id": new_announcement.announcement_id}

# 공지사항 상세보기 요청
async def get_announcement_detail(db: AsyncSession, announcement_id: int, employee_id: str):
    await db.execute(
            text("""SELECT set_config('app.current_employee_id', :emp_id, true) """),
            {"emp_id": employee_id}
        )
    
    query = (
        select(
            Announcement,
            Department.department_name,
            Employee.employee_name
        )
        .join(Department, Announcement.parent_department_code == Department.department_code)
        .join(Employee, Announcement.employee_id == Employee.employee_id)
        .where(Announcement.announcement_id == announcement_id)
    )
    
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")
    
    ann, dept_name, emp_name = row
    
    return AnnouncementDetailResponse(
        announcement_id=ann.announcement_id,
        title=ann.title,
        content=ann.content,
        parent_department_code=ann.parent_department_code,
        department_name=dept_name,
        employee_id=ann.employee_id,
        employee_name=emp_name,
        created_at=ann.created_at,
        updated_at=ann.updated_at
    )
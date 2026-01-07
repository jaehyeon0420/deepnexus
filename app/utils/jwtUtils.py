import jwt
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from app.core.config import settings
from app.schemas.model import MemberInfo

class JwtUtils:
    # 암호화 알고리즘과 시크릿 키 설정
    SECRET_KEY = settings.SECRET_KEY  # settings에 SECRET_KEY가 있다고 가정
    ALGORITHM = "HS256"
    
    # 공통: 토큰 생성 내부 함수
    @staticmethod
    def _create_token(data: dict, expires_delta: timedelta) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        
        # 임의의 문자열 (JTI: Unique Identifier) 추가 - 보안 강화 및 토큰 고유성 보장
        to_encode.update({
            "exp": expire,
            "jti": str(uuid.uuid4()) 
        })
        
        encoded_jwt = jwt.encode(to_encode, JwtUtils.SECRET_KEY, algorithm=JwtUtils.ALGORITHM)
        return encoded_jwt

    # 1. Access Token 발급 (유효시간 10분)
    @staticmethod
    def create_access_token(member_data: dict) -> str:
        expires_delta = timedelta(minutes=60)
        return JwtUtils._create_token(member_data, expires_delta)

    # 2. Refresh Token 발급 (유효시간 2주)
    @staticmethod
    def create_refresh_token(member_data: dict) -> str:
        expires_delta = timedelta(weeks=2)
        return JwtUtils._create_token(member_data, expires_delta)

    # 3. 토큰 검증 함수
    @staticmethod
    def validate_token(token: str) -> MemberInfo:
        try:
            # 토큰 디코딩 (서명 검증 + 만료 시간 검증 포함)
            payload = jwt.decode(token, JwtUtils.SECRET_KEY, algorithms=[JwtUtils.ALGORITHM])
            
            # 필요한 정보 추출
            employee_id = payload.get("employee_id")
            if employee_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰에 사용자 정보가 없습니다.")
            
            # MemberInfo 객체로 변환하여 리턴
            return MemberInfo(
                employee_id=payload.get("employee_id"),
                employee_name=payload.get("employee_name"),
                job_rank_id=payload.get("job_rank_id"),
                department_code=payload.get("department_code"),
                company_email=payload.get("company_email"),
                parent_department_code=payload.get("parent_department_code"),
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="토큰이 만료되었습니다.")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다.")
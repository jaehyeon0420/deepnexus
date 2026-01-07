from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from app.utils.jwtUtils import JwtUtils

# 헤더에서 'Authorization' 값을 추출하기 위한 스키마 정의
# auto_error=False로 설정하여, 토큰이 없어도 바로 403을 띄우지 않고 로직에서 처리
header_scheme = APIKeyHeader(name="Authorization", auto_error=False)

# 토큰 검증 대상이 아닌 엔드포인트 목록
NO_AUTH_URLS = [
    "/login",
    "/signup",
    "/refresh",
    "/docs",         # Swagger UI
    "/openapi.json", # Swagger 문서 데이터
    "/redoc"         # ReDoc UI
]

# 모든 요청에 대해 Access Token을 검증하는 전역 의존성 함수
async def check_access_token(request: Request, token: str = Depends(header_scheme)):
    
    # 현재 요청한 URL 경로 가져오기
    path = request.url.path

    # Whitelist에 포함된 경로는 검증 없이 통과
    if path in NO_AUTH_URLS:
        return

    # 토큰이 없는 경우 에러 처리
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요한 서비스 입니다."
        )

    # Bearer 제거 (프론트에서 'Bearer '를 붙여보내지 않음)
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    # 토큰 검증
    try:
        JwtUtils.validate_token(token)
    except Exception as e:
        # JwtUtils에서 발생한 에러를 그대로 전파
        raise e
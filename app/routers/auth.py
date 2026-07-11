from fastapi import APIRouter, HTTPException, status

from app.dependencies import DbSessionDep
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import (
    AuthService,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register_user(payload: RegisterRequest, db: DbSessionDep) -> TokenResponse:
    service = AuthService(db)
    try:
        user = await service.register(payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        ) from exc
    return TokenResponse(access_token=service.issue_access_token(user))


@router.post("/login", response_model=TokenResponse)
async def login_user(payload: LoginRequest, db: DbSessionDep) -> TokenResponse:
    service = AuthService(db)
    try:
        user = await service.authenticate(payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        ) from exc

    return TokenResponse(access_token=service.issue_access_token(user))

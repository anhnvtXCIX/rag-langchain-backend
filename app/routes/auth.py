from fastapi import APIRouter, HTTPException

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register_user(payload: RegisterRequest) -> TokenResponse:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/login", response_model=TokenResponse)
async def login_user(payload: LoginRequest) -> TokenResponse:
    raise HTTPException(status_code=501, detail="Not implemented")

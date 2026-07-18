import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest

logger = logging.getLogger(__name__)


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, payload: RegisterRequest) -> User:
        user = User(
            username=payload.username,
            email=payload.email,
            hashed_password=get_password_hash(payload.password),
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise UserAlreadyExistsError from exc
        await self.db.refresh(user)
        return user

    async def authenticate(self, payload: LoginRequest) -> User:
        logger.info("Authenticating user: %s", payload.username)
        result = await self.db.execute(
            select(User).where(User.username == payload.username)
        )
        user = result.scalar_one_or_none()

        if user is None or not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError
        return user

    @staticmethod
    def issue_access_token(user: User) -> str:
        return create_access_token(subject=user.username)

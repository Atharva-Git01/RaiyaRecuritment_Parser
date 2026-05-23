"""
RAIYA Auth Service — User registration, login, token management.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, Organization, OTPToken
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.logging_config import get_logger
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse

logger = get_logger("AuthService")


async def register_user(session: AsyncSession, req: SignupRequest) -> User:
    """Register a new user."""
    # Check if email already exists
    result = await session.execute(select(User).where(User.email == req.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("Email already registered")

    # Create or find organization
    org = None
    if req.org_code:
        result = await session.execute(
            select(Organization).where(Organization.org_code == req.org_code)
        )
        org = result.scalar_one_or_none()

    if not org:
        org = Organization(
            name="Default Organization",
            org_code=req.org_code or f"ORG-{uuid.uuid4().hex[:8].upper()}"
        )
        session.add(org)
        await session.flush()

    user = User(
        full_name=req.full_name,
        email=req.email,
        hashed_password=hash_password(req.password),
        org_id=org.id,
        role="recruiter",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info(f"User registered: {req.email}")
    return user


async def authenticate_user(session: AsyncSession, req: LoginRequest) -> Optional[TokenResponse]:
    """Authenticate user and return JWT tokens."""
    result = await session.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        return None

    if not verify_password(req.password, user.hashed_password):
        return None

    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    logger.info(f"User authenticated: {user.email}")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        full_name=user.full_name,
    )


async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by ID."""
    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    return result.scalar_one_or_none()

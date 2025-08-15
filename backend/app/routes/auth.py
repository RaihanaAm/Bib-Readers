# backend/app/routes/auth.py
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.db.session import get_session
from app.models.adherent import Adherent
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, MeOut
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

# tokenUrl is required by OAuth2PasswordBearer (not used by /docs password flow here)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.post("/register", response_model=MeOut, status_code=201)
async def register(payload: RegisterIn, session: AsyncSession = Depends(get_session)):
    """Create a new adherent with hashed password."""
    # Email uniqueness
    exists = await session.execute(select(Adherent).where(Adherent.email == payload.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user = Adherent(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return MeOut(id=user.id, name=user.name, email=user.email)


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, session: AsyncSession = Depends(get_session)):
    """Validate credentials and return a JWT access token."""
    res = await session.execute(select(Adherent).where(Adherent.email == payload.email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    token = create_access_token(
        subject=str(user.id),
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    return TokenOut(access_token=token)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> Adherent:
    """Resolve current user from JWT token."""
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
        sub = payload.get("sub")
        if not sub:
            raise creds_exc
    except JWTError:
        raise creds_exc

    res = await session.execute(select(Adherent).where(Adherent.id == int(sub)))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise creds_exc
    return user


@router.get("/me", response_model=MeOut)
async def me(current: Adherent = Depends(get_current_user)):
    """Return current user profile."""
    return MeOut(id=current.id, name=current.name, email=current.email)

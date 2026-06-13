from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
import bcrypt
from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database.database import local_session
from core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from models.models import Users


algorithm = ALGORITHM
ACCESS_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_EXPIRE_DAYS = REFRESH_TOKEN_EXPIRE_DAYS


def getdb():
    db = local_session()
    try:
        yield db
    finally:
        db.close()


def hash_passwd(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password_hash(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode("utf-8"))


def authenticate_user(db: Session, username: Optional[str], email: Optional[str], password: str) -> Optional[Users]:
    q = db.query(Users)
    if email:
        user = q.filter(Users.email == email).first()
    else:
        user = q.filter(Users.user_name == username).first()

    if not user:
        return None

    if not verify_password_hash(password, user.hash_password):
        return None

    return user


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user: Users) -> str:
    exp = _now() + timedelta(minutes=int(ACCESS_EXPIRE_MINUTES))
    payload = {
        "iss": "Tech_comm",
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value,
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=algorithm)


def create_refresh_token(user: Users) -> str:
    exp = _now() + timedelta(days=int(REFRESH_EXPIRE_DAYS))
    payload = {
        "iss": "Tech_comm",
        "user_id": user.id,
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=algorithm)


def verify_token(token: str, allow_refresh: bool = False) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    token_type = payload.get("type")
    if allow_refresh:
        if token_type != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    else:
        if token_type != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    return payload


def get_token_from_header(authorization: str | None = Header(None)) -> str:
    if authorization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header must use Bearer token")

    return authorization.split(" ", 1)[1]


def get_current_user(token: str = Depends(get_token_from_header), db: Session = Depends(getdb)) -> Users:
    payload = verify_token(token=token)
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.query(Users).filter(Users.id == user_id, Users.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


def get_current_active_user(current_user: Users = Depends(get_current_user)) -> Users:
    return current_user


def require_admin(current_user: Users = Depends(get_current_user)) -> Users:
    if current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


def require_customer(current_user: Users = Depends(get_current_user)) -> Users:
    if current_user.role.value != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer privileges required")
    return current_user

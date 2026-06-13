from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models.models import Users
from schemas.schemas import (login_inputs, registration_inputs)
from utils.commonservices import (complete_registration, getdb)
from core import security


router = APIRouter(tags=["Authentication"])


@router.post('/auth/register')
async def sign_in(db: Annotated[Session, Depends(getdb)], clsinput: registration_inputs):
    inputs = Users(
        first_name=clsinput.first_name,
        last_name=clsinput.last_name,
        user_name=clsinput.user_name,
        email=clsinput.email,
        contact=clsinput.contact,
        hash_password=security.hash_passwd(clsinput.password),
        DOB=clsinput.DOB,
    )
    result = complete_registration(
        email=clsinput.email,
        username=clsinput.user_name,
        contact=str(clsinput.contact),
        first_name=clsinput.first_name,
        last_name=clsinput.last_name,
        db=db,
    )
    if result == "Done":
        try:
            db.add(inputs)
            db.commit()
            db.refresh(inputs)
            return {"message": f"{clsinput.user_name} registered!"}
        except Exception as e:
            db.rollback()
            raise
    return result


@router.post('/auth/login')
def log_in(db: Annotated[Session, Depends(getdb)], clsinput: login_inputs):
    username = clsinput.user_name
    password = clsinput.password
    email = clsinput.email

    user = security.authenticate_user(db=db, username=username, email=email, password=password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    access_token = security.create_access_token(user)
    refresh_token = security.create_refresh_token(user)

    return {
        "message": "Logged In!",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post('/auth/refresh')
def refresh_token(refresh: dict = Body(...)):
    token = refresh.get("refresh_token")
    if not token:
        raise HTTPException(status_code=400, detail="refresh_token required")

    payload = security.verify_token(token, allow_refresh=True)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    db = next(getdb())
    try:
        user = db.query(Users).filter(Users.id == user_id, Users.is_deleted == False).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        access_token = security.create_access_token(user)
        return {"access_token": access_token, "token_type": "bearer"}
    finally:
        db.close()



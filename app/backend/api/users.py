from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.models import  Users
from schemas.userSchemas import user_update_inputs
from utils.commonservices import ( getdb, validate_contact, validate_username)
from core.security import (get_current_user)



router = APIRouter(tags=["Users"])




@router.get('/auth/profile')
def getUser(db: Annotated[Session, Depends(getdb)], current_user = Depends(get_current_user)):
    user = current_user
    return {"Username": user.user_name,
            "Contact": user.contact,
            "User_id": user.id,
            "First_name": user.first_name,
            "Last_name": user.last_name}


@router.put('/user/profile/update')
def updateUser(
    db: Annotated[Session, Depends(getdb)],
    clsinput: user_update_inputs,
    current_user = Depends(get_current_user),
):
    user = current_user

    if clsinput.user_name is not None:
        existing_user = db.query(Users).filter(
            Users.user_name == clsinput.user_name,
            Users.id != user.id
        ).first()

        if existing_user:
            return {"message": "Username already taken"}

        if not validate_username(clsinput.user_name):
            return {"message": "Invalid username"}

        user.user_name = clsinput.user_name

    if clsinput.first_name is not None:
        user.first_name = clsinput.first_name

    if clsinput.last_name is not None:
        user.last_name = clsinput.last_name

    if clsinput.contact is not None:
        if not validate_contact(clsinput.contact):
            return {"message": "Invalid contact"}

        user.contact = clsinput.contact

    if clsinput.DOB is not None:
        user.DOB = clsinput.DOB

    try:
        db.commit()
        db.refresh(user)
        return {"message": "User updated successfully"}
    except Exception:
        db.rollback()
        raise
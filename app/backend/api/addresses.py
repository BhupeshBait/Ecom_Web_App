from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session
from models.models import (Addresses)
from schemas.addressSchemas import ( address_inputs, address_update
                             )
from utils.commonservices import  getdb
from core.security import (get_current_user)



countryList = {
    "India": [
        "Maharashtra",
        "Karnataka",
        "Tamil Nadu",
        "Uttar Pradesh",
        "Gujarat",
        "Rajasthan",
        "West Bengal",
        "Punjab",
        "Bihar",
        "Kerala"
    ],
    "United States": [
        "California",
        "Texas",
        "Florida",
        "New York",
        "Illinois",
        "Pennsylvania",
        "Ohio",
        "Georgia",
        "North Carolina",
        "Michigan"
    ]
}


router = APIRouter(tags=["Addresses"])

@router.post('/add/address')
def add_address(db: Annotated[Session, Depends(getdb)], clsinput: address_inputs, current_user = Depends(get_current_user)):
    user = current_user
    user_inputs = Addresses(
        user_id=user.id,
        street=clsinput.Street,
        city=clsinput.City,
        state=clsinput.State,
        country=clsinput.Country,
        postal_code=clsinput.Postal_code,
        address_line_1=clsinput.address_line_1,
        address_line_2=clsinput.address_line_2,
        district=clsinput.district,
        landmark=clsinput.landmark
    )
    if not clsinput.Country in countryList.keys():
        return {"message": "Enter a valid Country name"}

    if not clsinput.State in countryList[clsinput.Country]:
        return {"message": "Enetr a valid State name"}

    try:
        db.add(user_inputs)
        db.commit()
        db.refresh(user_inputs)
        return {"message": "Address added!"}
    except Exception:
        db.rollback()
        raise


@router.get('/get/addresses')
def get_address(db: Annotated[Session, Depends(getdb)], current_user = Depends(get_current_user)):
    user = current_user
    result = db.query(Addresses).filter(
        and_(
            Addresses.user_id == user.id,
            Addresses.is_deleted == False)).all()
    return {"Addresses": result}


@router.put('/update/address/{id}')
def updateAddress(
    id: int,
    clsinput: address_update,
    db: Annotated[Session, Depends(getdb)],
    current_user = Depends(get_current_user)
):
    user = current_user
    address = db.query(Addresses).filter(
        Addresses.id == id,
        Addresses.user_id == user.id,
        Addresses.is_deleted == False
    ).first()

    if not address:
        return {"message": "Address not found"}

    if clsinput.Country is not None:
        if clsinput.Country not in countryList:
            return {"message": "Invalid country"}

        address.country = clsinput.Country

    if clsinput.State is not None:
        country = clsinput.Country or address.country

        if country not in countryList:
            return {"message": "Invalid country"}

        if clsinput.State not in countryList[country]:
            return {"message": "Invalid state"}

        address.state = clsinput.State

    if clsinput.City is not None:
        address.city = clsinput.City

    if clsinput.Street is not None:
        address.street = clsinput.Street

    if clsinput.Postal_code is not None:
        address.postal_code = clsinput.Postal_code

    if clsinput.address_line_1 is not None:
        address.address_line_1 = clsinput.address_line_1

    if clsinput.address_line_2 is not None:
        address.address_line_2 = clsinput.address_line_2

    if clsinput.landmark is not None:
        address.landmark = clsinput.landmark

    if clsinput.district is not None:
        address.district = clsinput.district

    try:
        db.commit()
        db.refresh(address)
        return {"message": "Address updated"}
    except Exception:
        db.rollback()
        raise


@router.put('/remove/address/{id}')
def deleteAddress(id: int, db: Annotated[Session, Depends(getdb)], current_user = Depends(get_current_user)):
    user = current_user
    address = db.query(Addresses).filter(
        and_(Addresses.id == id, Addresses.user_id == user.id)).first()
    try:
        if address:
            address.is_deleted = True
        db.commit()
        return {"message": "Address removed"}
    except Exception:
        db.rollback()
        raise





from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid
from datetime import datetime
from models.models import (
    Payments,
    Orders,
    PaymentStatus,
    OrderStatus
)

from schemas.paymentSchemas import (
    payment_create_inputs,
    payment_verify_inputs
)

from utils.commonservices import getdb
from core.security import get_current_user

router = APIRouter(tags=["Payments"])


@router.post("/payment/create")
def create_payment(
    clsinput: payment_create_inputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    order = db.query(Orders).filter(
        and_(
            Orders.id == clsinput.order_id,
            Orders.user_id == user.id,
            Orders.is_deleted == False
        )
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    existing_payment = db.query(Payments).filter(
        Payments.order_id == order.id
    ).first()

    if existing_payment:
        raise HTTPException(
            status_code=409,
            detail="Payment already created"
        )

    payment_reference = (
        "PAY-" +
        uuid.uuid4().hex[:12].upper()
    )

    payment = Payments(
        order_id=order.id,
        payment_reference=payment_reference,
        payment_method=clsinput.payment_method,
        amount=order.final_amount,
        status=PaymentStatus.PENDING
    )

    try:
        db.add(payment)

        db.commit()

        db.refresh(payment)
        return {
            "payment_id": payment.id,
            "payment_reference": payment.payment_reference,
            "amount": payment.amount,
            "status": payment.status.value,
            "message": "Payment created successfully"
        }
    except Exception:
        db.rollback()
        raise


@router.post("/payment/verify")
def verify_payment(
    clsinput: payment_verify_inputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    payment = (
        db.query(Payments)
        .join(Orders)
        .filter(
            Payments.payment_reference
            == clsinput.payment_reference,

            Orders.user_id == user.id,

            Payments.is_deleted == False
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    if payment.status == PaymentStatus.SUCCESS:
        raise HTTPException(
            status_code=409,
            detail="Payment already verified"
        )

    payment.status = PaymentStatus.SUCCESS

    order = db.query(Orders).filter(
        Orders.id == payment.order_id
    ).first()

    order.status = OrderStatus.PROCESSING

    payment.paid_at = datetime.utcnow()

    try:
        db.commit()

        db.refresh(payment)
    except Exception:
        db.rollback()
        raise

    return {
        "payment_id": payment.id,
        "payment_reference": payment.payment_reference,
        "payment_status": payment.status.value,
        "order_status": order.status.value,
        "message": "Payment verified successfully"
    }


@router.get("/payment/{payment_id}")
def get_payment_details(
    payment_id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    payment = (
        db.query(Payments)
        .join(Orders)
        .filter(
            Payments.id == payment_id,
            Orders.user_id == user.id,
            Payments.is_deleted == False
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    return {
        "payment_id": payment.id,
        "payment_reference": payment.payment_reference,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "payment_method": payment.payment_method,
        "payment_gateway": payment.payment_gateway,
        "status": payment.status.value,
        "transaction_id": payment.transaction_id,
        "paid_at": payment.paid_at,
        "created_at": payment.created_at
    }
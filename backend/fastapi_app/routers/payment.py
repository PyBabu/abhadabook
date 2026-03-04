from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from database import get_db

router = APIRouter()


class PaymentCreate(BaseModel):
    booking_id: int
    payment_method: str = "upi"


@router.post("/create")
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    booking = db.execute(
        text("SELECT * FROM bookings WHERE id = :id"),
        {"id": payment.booking_id}
    ).fetchone()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db.execute(
        text("""
            INSERT INTO payments (booking_id, amount, payment_method, status, created_at)
            VALUES (:booking_id, :amount, :payment_method, 'pending', NOW())
        """),
        {
            "booking_id": payment.booking_id,
            "amount": booking.total_amount,
            "payment_method": payment.payment_method
        }
    )
    db.commit()

    return {
        "success": True,
        "booking_id": payment.booking_id,
        "amount": float(booking.total_amount),
        "message": "Payment initiated"
    }


@router.put("/confirm/{booking_id}")
def confirm_payment(booking_id: int, db: Session = Depends(get_db)):
    db.execute(
        text("UPDATE payments SET status = 'success', paid_at = NOW() WHERE booking_id = :id"),
        {"id": booking_id}
    )
    db.execute(
        text("UPDATE bookings SET status = 'confirmed', updated_at = NOW() WHERE id = :id"),
        {"id": booking_id}
    )
    db.commit()

    return {
        "success": True,
        "message": "Payment confirmed! Booking is now confirmed.",
        "booking_id": booking_id
    }
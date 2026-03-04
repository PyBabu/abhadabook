from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import sys, os, qrcode, uuid
from io import BytesIO
import base64

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from database import get_db

router = APIRouter()


def generate_ticket_number():
    return "ABK-" + str(uuid.uuid4())[:8].upper()


def generate_qr_code(data: str) -> str:
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode()


@router.post("/generate/{booking_id}")
def generate_ticket(booking_id: int, db: Session = Depends(get_db)):
    booking = db.execute(
        text("SELECT * FROM bookings WHERE id = :id"),
        {"id": booking_id}
    ).fetchone()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "confirmed":
        raise HTTPException(status_code=400, detail="Booking is not confirmed yet")

    existing = db.execute(
        text("SELECT * FROM tickets WHERE booking_id = :id"),
        {"id": booking_id}
    ).fetchone()

    if existing:
        return {
            "success": True,
            "ticket_number": existing.ticket_number,
            "qr_code": existing.qr_code_data,
            "message": "Ticket already exists"
        }

    ticket_number = generate_ticket_number()
    qr_data = f"ABADHABOOK|{ticket_number}|{booking_id}|{booking.booking_date}|{booking.number_of_persons}"
    qr_code_base64 = generate_qr_code(qr_data)

    db.execute(
        text("""
            INSERT INTO tickets (booking_id, ticket_number, qr_code_data, is_used, created_at)
            VALUES (:booking_id, :ticket_number, :qr_code_data, 0, NOW())
        """),
        {
            "booking_id": booking_id,
            "ticket_number": ticket_number,
            "qr_code_data": qr_code_base64
        }
    )
    db.commit()

    return {
        "success": True,
        "ticket_number": ticket_number,
        "qr_code": qr_code_base64,
        "booking_date": str(booking.booking_date),
        "number_of_persons": booking.number_of_persons
    }


@router.get("/{ticket_number}")
def get_ticket(ticket_number: str, db: Session = Depends(get_db)):
    ticket = db.execute(
        text("""
            SELECT t.*, b.booking_date, b.number_of_persons, b.total_amount,
                   u.name, u.mobile_number
            FROM tickets t
            JOIN bookings b ON t.booking_id = b.id
            JOIN users u ON b.user_id = u.id
            WHERE t.ticket_number = :ticket_number
        """),
        {"ticket_number": ticket_number}
    ).fetchone()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {
        "ticket_number": ticket.ticket_number,
        "user_name": ticket.name,
        "mobile_number": ticket.mobile_number,
        "booking_date": str(ticket.booking_date),
        "number_of_persons": ticket.number_of_persons,
        "total_amount": float(ticket.total_amount),
        "is_used": ticket.is_used,
        "qr_code": ticket.qr_code_data
    }
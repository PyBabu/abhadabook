from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from database import get_db

router = APIRouter()


# ── Pydantic Schemas ──────────────────────────────────────────────
class BookingCreate(BaseModel):
    user_id: int
    booking_date: date
    number_of_persons: int
    special_occasion: Optional[str] = None


# ── Helper: Check Booking Cutoff Time ────────────────────────────
def is_booking_allowed(booking_date: date) -> bool:
    now = datetime.now()
    today = now.date()
    cutoff_hour = int(os.getenv('BOOKING_CUTOFF_HOUR', 9))

    if booking_date > today:
        return True
    if booking_date == today:
        return now.hour < cutoff_hour
    return False


# ── Helper: Check Capacity ────────────────────────────────────────
def get_available_capacity(booking_date: date, db: Session) -> int:
    result = db.execute(
        text("""
            SELECT COALESCE(SUM(number_of_persons), 0) as total 
            FROM bookings 
            WHERE booking_date = :date AND status != 'cancelled'
        """),
        {"date": booking_date}
    ).fetchone()

    total_booked = int(result.total) if result else 0
    max_capacity = int(os.getenv('MAX_CAPACITY_PER_DAY', 200))
    return max_capacity - total_booked


# ── API: Get Available Capacity ─── MUST BE BEFORE /{booking_id}
@router.get("/availability/{check_date}")
def check_availability(check_date: date, db: Session = Depends(get_db)):
    available = get_available_capacity(check_date, db)
    max_capacity = int(os.getenv('MAX_CAPACITY_PER_DAY', 200))
    is_allowed = is_booking_allowed(check_date)

    return {
        "date": str(check_date),
        "total_capacity": max_capacity,
        "available_spots": available,
        "is_booking_open": is_allowed and available > 0,
        "message": "Booking is open" if (is_allowed and available > 0) else "Booking is closed for this date"
    }


# ── API: Get User Bookings ─── MUST BE BEFORE /{booking_id}
@router.get("/user/{user_id}")
def get_user_bookings(user_id: int, db: Session = Depends(get_db)):
    bookings = db.execute(
        text("""
            SELECT b.*, t.ticket_number, t.is_used 
            FROM bookings b 
            LEFT JOIN tickets t ON b.id = t.booking_id
            WHERE b.user_id = :user_id 
            ORDER BY b.created_at DESC
        """),
        {"user_id": user_id}
    ).fetchall()

    result = []
    for b in bookings:
        result.append({
            "booking_id": b.id,
            "booking_date": str(b.booking_date),
            "number_of_persons": b.number_of_persons,
            "total_amount": float(b.total_amount),
            "status": b.status,
            "ticket_number": b.ticket_number,
            "is_used": bool(b.is_used),
            "created_at": str(b.created_at)
        })

    return {
        "user_id": user_id,
        "total_bookings": len(result),
        "bookings": result
    }


# ── API: Get User by Mobile ─── MUST BE BEFORE /{booking_id}
@router.get("/user/mobile/{mobile}")
def get_or_create_user(mobile: str, name: str = "Guest", city: str = "", db: Session = Depends(get_db)):
    user = db.execute(
        text("SELECT * FROM users WHERE mobile_number = :mobile"),
        {"mobile": mobile}
    ).fetchone()

    if user:
        return {"user_id": user.id, "name": user.name, "mobile": user.mobile_number}

    result = db.execute(
        text("""
            INSERT INTO users (name, mobile_number, city, is_active, created_at, updated_at)
            VALUES (:name, :mobile, :city, 1, NOW(), NOW())
        """),
        {"name": name, "mobile": mobile, "city": city}
    )
    db.commit()
    return {"user_id": result.lastrowid, "name": name, "mobile": mobile}


# ── API: Create Booking ───────────────────────────────────────────
@router.post("/create")
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):

    if booking.booking_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot book for a past date")

    if not is_booking_allowed(booking.booking_date):
        raise HTTPException(status_code=400, detail="Booking for today is closed after 9:00 AM. Please book for tomorrow.")

    if booking.number_of_persons < 1:
        raise HTTPException(status_code=400, detail="Number of persons must be at least 1")

    if booking.number_of_persons > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 persons allowed per booking")

    available = get_available_capacity(booking.booking_date, db)
    if available <= 0:
        raise HTTPException(status_code=400, detail=f"No capacity available for {booking.booking_date}. Please join the waiting list.")

    if booking.number_of_persons > available:
        raise HTTPException(status_code=400, detail=f"Only {available} spots available for {booking.booking_date}")

    user = db.execute(
        text("SELECT id, name FROM users WHERE id = :id AND is_active = 1"),
        {"id": booking.user_id}
    ).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please login again.")

    price_per_person = int(os.getenv('PRICE_PER_PERSON', 130))
    total_amount = booking.number_of_persons * price_per_person

    result = db.execute(
        text("""
            INSERT INTO bookings 
            (user_id, booking_date, number_of_persons, total_amount, status, special_occasion, created_at, updated_at)
            VALUES (:user_id, :booking_date, :number_of_persons, :total_amount, 'pending', :special_occasion, NOW(), NOW())
        """),
        {
            "user_id": booking.user_id,
            "booking_date": booking.booking_date,
            "number_of_persons": booking.number_of_persons,
            "total_amount": total_amount,
            "special_occasion": booking.special_occasion
        }
    )
    db.commit()

    return {
        "success": True,
        "message": "Booking created successfully!",
        "booking_id": result.lastrowid,
        "booking_date": str(booking.booking_date),
        "number_of_persons": booking.number_of_persons,
        "total_amount": total_amount,
        "price_per_person": price_per_person,
        "status": "pending"
    }


# ── API: Cancel Booking ───────────────────────────────────────────
@router.put("/cancel/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.execute(
        text("SELECT * FROM bookings WHERE id = :id"),
        {"id": booking_id}
    ).fetchone()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status == 'cancelled':
        raise HTTPException(status_code=400, detail="Booking is already cancelled")

    db.execute(
        text("UPDATE bookings SET status = 'cancelled', updated_at = NOW() WHERE id = :id"),
        {"id": booking_id}
    )
    db.commit()

    return {"success": True, "message": "Booking cancelled", "booking_id": booking_id}
from datetime import date

@router.get("/today-stats")
def today_stats(db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT COUNT(*) as total_scanned
            FROM tickets t
            JOIN bookings b ON t.booking_id = b.id
            WHERE b.booking_date = :today
              AND t.is_used = 1
        """),
        {"today": date.today()}
    ).fetchone()

    return {
        "date": str(date.today()),
        "total_scanned": int(result.total_scanned) if result else 0
    }

# ── API: Get Single Booking ─── KEEP THIS LAST
@router.get("/{booking_id}")
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.execute(
        text("""
            SELECT b.*, u.name, u.mobile_number 
            FROM bookings b 
            JOIN users u ON b.user_id = u.id 
            WHERE b.id = :id
        """),
        {"id": booking_id}
    ).fetchone()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return {
        "booking_id": booking.id,
        "user_name": booking.name,
        "mobile_number": booking.mobile_number,
        "booking_date": str(booking.booking_date),
        "number_of_persons": booking.number_of_persons,
        "total_amount": float(booking.total_amount),
        "status": booking.status,
        "special_occasion": booking.special_occasion,
        "created_at": str(booking.created_at)
    }
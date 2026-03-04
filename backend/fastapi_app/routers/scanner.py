from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime, date
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from database import get_db

router = APIRouter()


class ScanRequest(BaseModel):
    ticket_number: str


@router.post("/verify")
def verify_ticket(scan: ScanRequest, db: Session = Depends(get_db)):

    ticket_number = scan.ticket_number.strip().upper()

    # Basic format validation
    if not ticket_number.startswith("ABK-"):
        db.execute(text("""
            INSERT INTO scan_logs
            (ticket_number, scan_result, scan_message)
            VALUES (:tn, 'invalid', 'Invalid ticket format')
        """), {"tn": ticket_number})
        db.commit()

        return {"valid": False, "status": "invalid_format"}

    # Lock row to prevent double scan
    ticket = db.execute(text("""
        SELECT t.id, t.ticket_number, t.is_used, t.used_at,
               b.booking_date, b.number_of_persons,
               u.name, u.mobile_number
        FROM tickets t
        JOIN bookings b ON t.booking_id = b.id
        JOIN users u ON b.user_id = u.id
        WHERE t.ticket_number = :ticket_number
        FOR UPDATE
    """), {"ticket_number": ticket_number}).fetchone()

    if not ticket:
        db.execute(text("""
            INSERT INTO scan_logs
            (ticket_number, scan_result, scan_message)
            VALUES (:tn, 'invalid', 'Ticket not found')
        """), {"tn": ticket_number})
        db.commit()

        return {"valid": False, "status": "not_found"}

    # Already used
    if ticket.is_used:
        db.execute(text("""
            INSERT INTO scan_logs
            (ticket_number, user_name, mobile_number,
             booking_date, number_of_persons,
             scan_result, scan_message)
            VALUES
            (:tn, :name, :mobile,
             :bdate, :persons,
             'used', 'Ticket already used')
        """), {
            "tn": ticket.ticket_number,
            "name": ticket.name,
            "mobile": ticket.mobile_number,
            "bdate": ticket.booking_date,
            "persons": ticket.number_of_persons
        })
        db.commit()

        return {
            "valid": False,
            "status": "already_used",
            "ticket_number": ticket.ticket_number,
            "user_name": ticket.name
        }

    # Wrong date protection
    if ticket.booking_date != date.today():
        db.execute(text("""
            INSERT INTO scan_logs
            (ticket_number, user_name, mobile_number,
             booking_date, number_of_persons,
             scan_result, scan_message)
            VALUES
            (:tn, :name, :mobile,
             :bdate, :persons,
             'wrong_date', 'Ticket not valid for today')
        """), {
            "tn": ticket.ticket_number,
            "name": ticket.name,
            "mobile": ticket.mobile_number,
            "bdate": ticket.booking_date,
            "persons": ticket.number_of_persons
        })
        db.commit()

        return {"valid": False, "status": "wrong_date"}

    # Mark ticket as used
    db.execute(text("""
        UPDATE tickets
        SET is_used = 1,
            used_at = NOW()
        WHERE id = :ticket_id
    """), {"ticket_id": ticket.id})

    # Log success
    db.execute(text("""
        INSERT INTO scan_logs
        (ticket_number, user_name, mobile_number,
         booking_date, number_of_persons,
         scan_result, scan_message)
        VALUES
        (:tn, :name, :mobile,
         :bdate, :persons,
         'valid', 'Valid entry')
    """), {
        "tn": ticket.ticket_number,
        "name": ticket.name,
        "mobile": ticket.mobile_number,
        "bdate": ticket.booking_date,
        "persons": ticket.number_of_persons
    })

    db.commit()

    return {
        "valid": True,
        "status": "success",
        "ticket_number": ticket.ticket_number,
        "user_name": ticket.name,
        "mobile_number": ticket.mobile_number,
        "booking_date": str(ticket.booking_date),
        "number_of_persons": ticket.number_of_persons,
        "scanned_at": datetime.now().strftime("%d %b %Y %I:%M %p")
    }


    # for log files

    # ── GET /stats/today ──────────────────────────────────────────
@router.get("/stats/today")
def today_stats(db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT
                SUM(scan_result = 'valid')      AS valid_count,
                SUM(scan_result = 'used')        AS used_count,
                SUM(scan_result = 'invalid')     AS invalid_count,
                SUM(scan_result = 'wrong_date')  AS wrong_date_count,
                COUNT(*)                          AS total_count
            FROM scan_logs
            WHERE DATE(scanned_at) = :today
        """),
        {"today": date.today()}
    ).fetchone()

    return {
        "date"       : str(date.today()),
        "valid"      : int(result.valid_count       or 0),
        "used"       : int(result.used_count        or 0),
        "invalid"    : int(result.invalid_count     or 0),
        "wrong_date" : int(result.wrong_date_count  or 0),
        "total"      : int(result.total_count       or 0)
    }


# ── GET /logs/today ───────────────────────────────────────────
@router.get("/logs/today")
def today_logs(db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT ticket_number, user_name, mobile_number,
                   booking_date, number_of_persons,
                   scan_result, scan_message, scanned_at
            FROM scan_logs
            WHERE DATE(scanned_at) = :today
            ORDER BY scanned_at DESC
            LIMIT 30
        """),
        {"today": date.today()}
    ).fetchall()

    logs = []
    for r in rows:
        logs.append({
            "ticket_number"     : r.ticket_number,
            "user_name"         : r.user_name         or "—",
            "mobile_number"     : r.mobile_number      or "—",
            "booking_date"      : str(r.booking_date)  if r.booking_date else "—",
            "number_of_persons" : r.number_of_persons  or "—",
            "scan_result"       : r.scan_result,
            "scan_message"      : r.scan_message,
            "scanned_at"        : r.scanned_at.strftime("%I:%M:%S %p") if r.scanned_at else "—"
        })

    return {
        "date"  : str(date.today()),
        "count" : len(logs),
        "logs"  : logs
    }
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from database import get_db

router = APIRouter()


# ── Staff Key Auth ─────────────────────────────────────────────
def verify_staff(x_staff_key: str = Header(None)):
    if x_staff_key != "TempleSecure123":
        raise HTTPException(status_code=403, detail="Unauthorized")


# ══════════════════════════════════════════════════════════════
#  GET /api/analytics/dashboard
#  Returns ALL analytics data in one call — used by the HTML page
# ══════════════════════════════════════════════════════════════
@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    staff: str = Depends(verify_staff)
):
    today = date.today()

    # ── 1. Summary KPIs ──────────────────────────────────────
    summary = db.execute(text("""
        SELECT
            COUNT(*)                                               AS total_bookings,
            COALESCE(SUM(number_of_persons), 0)                   AS total_persons,
            COALESCE(SUM(CASE WHEN status='confirmed'
                         THEN total_amount ELSE 0 END), 0)        AS total_revenue,
            COUNT(CASE WHEN status='confirmed' THEN 1 END)        AS confirmed_bookings,
            COUNT(CASE WHEN status='cancelled' THEN 1 END)        AS cancelled_bookings,
            COUNT(CASE WHEN status='pending'   THEN 1 END)        AS pending_bookings
        FROM bookings
        WHERE YEAR(booking_date)  = YEAR(:today)
          AND MONTH(booking_date) = MONTH(:today)
    """), {"today": today}).fetchone()

    # tickets scanned this month
    scanned = db.execute(text("""
        SELECT COUNT(*) AS scanned
        FROM tickets t
        JOIN bookings b ON t.booking_id = b.id
        WHERE t.is_used = 1
          AND YEAR(b.booking_date)  = YEAR(:today)
          AND MONTH(b.booking_date) = MONTH(:today)
    """), {"today": today}).fetchone()

    # ── 2. Bookings per day — last 30 days ───────────────────
    daily_rows = db.execute(text("""
        SELECT
            booking_date,
            COUNT(*)                                               AS bookings,
            COALESCE(SUM(number_of_persons), 0)                   AS persons,
            COALESCE(SUM(CASE WHEN status='confirmed'
                         THEN total_amount ELSE 0 END), 0)        AS revenue
        FROM bookings
        WHERE booking_date >= DATE_SUB(:today, INTERVAL 29 DAY)
          AND booking_date <= :today
        GROUP BY booking_date
        ORDER BY booking_date ASC
    """), {"today": today}).fetchall()

    daily = []
    for r in daily_rows:
        daily.append({
            "date"     : str(r.booking_date),
            "bookings" : int(r.bookings),
            "persons"  : int(r.persons),
            "revenue"  : float(r.revenue)
        })

    # ── 3. Payment method breakdown ──────────────────────────
    pay_rows = db.execute(text("""
        SELECT
            COALESCE(payment_method, 'unknown') AS method,
            COUNT(*)                             AS count,
            COALESCE(SUM(amount), 0)             AS total
        FROM payments
        WHERE status = 'success'
        GROUP BY payment_method
        ORDER BY count DESC
    """)).fetchall()

    payments = []
    for r in pay_rows:
        payments.append({
            "method" : str(r.method),
            "count"  : int(r.count),
            "total"  : float(r.total)
        })

    # ── 4. Special occasions breakdown ───────────────────────
    occ_rows = db.execute(text("""
        SELECT
            COALESCE(NULLIF(special_occasion,''), 'none') AS occasion,
            COUNT(*)                                        AS count,
            COALESCE(SUM(number_of_persons), 0)            AS persons
        FROM bookings
        WHERE status = 'confirmed'
        GROUP BY special_occasion
        ORDER BY count DESC
    """)).fetchall()

    occasions = []
    for r in occ_rows:
        occasions.append({
            "occasion" : str(r.occasion),
            "count"    : int(r.count),
            "persons"  : int(r.persons)
        })

    # ── 5. Peak booking days (all time top 7) ────────────────
    peak_rows = db.execute(text("""
        SELECT
            booking_date,
            COUNT(*)                            AS bookings,
            COALESCE(SUM(number_of_persons), 0) AS persons,
            COALESCE(SUM(CASE WHEN status='confirmed'
                         THEN total_amount ELSE 0 END), 0) AS revenue
        FROM bookings
        WHERE status != 'cancelled'
        GROUP BY booking_date
        ORDER BY persons DESC
        LIMIT 7
    """)).fetchall()

    peak = []
    for r in peak_rows:
        peak.append({
            "date"     : str(r.booking_date),
            "bookings" : int(r.bookings),
            "persons"  : int(r.persons),
            "revenue"  : float(r.revenue)
        })

    # ── 6. Last 10 bookings ──────────────────────────────────
    recent_rows = db.execute(text("""
        SELECT
            b.id, u.name, u.mobile_number,
            b.booking_date, b.number_of_persons,
            b.total_amount, b.status,
            COALESCE(NULLIF(b.special_occasion,''), 'none') AS occasion,
            b.created_at
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        ORDER BY b.created_at DESC
        LIMIT 10
    """)).fetchall()

    recent = []
    for r in recent_rows:
        recent.append({
            "id"              : r.id,
            "name"            : r.name,
            "mobile"          : r.mobile_number,
            "booking_date"    : str(r.booking_date),
            "persons"         : r.number_of_persons,
            "amount"          : float(r.total_amount),
            "status"          : r.status,
            "occasion"        : r.occasion,
            "created_at"      : str(r.created_at)
        })

    # ── 7. All-time totals ───────────────────────────────────
    alltime = db.execute(text("""
        SELECT
            COUNT(*)                                        AS total_bookings,
            COALESCE(SUM(number_of_persons), 0)             AS total_persons,
            COALESCE(SUM(CASE WHEN status='confirmed'
                         THEN total_amount ELSE 0 END), 0)  AS total_revenue
        FROM bookings
    """)).fetchone()

    return {
        "generated_at"  : str(today),
        "this_month"    : {
            "total_bookings"    : int(summary.total_bookings),
            "total_persons"     : int(summary.total_persons),
            "total_revenue"     : float(summary.total_revenue),
            "confirmed"         : int(summary.confirmed_bookings),
            "cancelled"         : int(summary.cancelled_bookings),
            "pending"           : int(summary.pending_bookings),
            "tickets_scanned"   : int(scanned.scanned)
        },
        "all_time"      : {
            "total_bookings"    : int(alltime.total_bookings),
            "total_persons"     : int(alltime.total_persons),
            "total_revenue"     : float(alltime.total_revenue)
        },
        "daily_last_30" : daily,
        "payment_methods": payments,
        "occasions"     : occasions,
        "peak_days"     : peak,
        "recent_bookings": recent
    }
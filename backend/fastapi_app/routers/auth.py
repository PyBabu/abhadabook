from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime, timedelta
import random
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from database import get_db

router = APIRouter()


class SendOTP(BaseModel):
    mobile_number: str


class VerifyOTP(BaseModel):
    mobile_number: str
    otp_code: str
    name: str
    city: str = None


# ✅ Send OTP
@router.post("/send-otp")
def send_otp(data: SendOTP, db: Session = Depends(get_db)):

    if len(data.mobile_number) != 10:
        raise HTTPException(status_code=400, detail="Invalid mobile number")

    otp = str(random.randint(100000, 999999))
    expires_at = datetime.now() + timedelta(minutes=5)

    # delete old otp
    db.execute(
        text("DELETE FROM otp_verifications WHERE mobile_number = :mobile"),
        {"mobile": data.mobile_number}
    )

    db.execute(
        text("""
            INSERT INTO otp_verifications 
            (mobile_number, otp_code, is_verified, created_at, expires_at)
            VALUES (:mobile, :otp, 0, NOW(), :expires_at)
        """),
        {
            "mobile": data.mobile_number,
            "otp": otp,
            "expires_at": expires_at
        }
    )

    db.commit()

    # 🔥 FREE METHOD → print in terminal
    print(f"OTP for {data.mobile_number} is: {otp}")

    return {
        "success": True,
        "message": "OTP sent successfully (check terminal for OTP)"
    }


# ✅ Verify OTP
@router.post("/verify-otp")
def verify_otp(data: VerifyOTP, db: Session = Depends(get_db)):

    otp_record = db.execute(
        text("""
            SELECT * FROM otp_verifications 
            WHERE mobile_number = :mobile AND otp_code = :otp
        """),
        {
            "mobile": data.mobile_number,
            "otp": data.otp_code
        }
    ).fetchone()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if otp_record.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="OTP expired")

    # mark verified
    db.execute(
        text("""
            UPDATE otp_verifications 
            SET is_verified = 1 
            WHERE id = :id
        """),
        {"id": otp_record.id}
    )

    # check if user exists
    user = db.execute(
        text("SELECT * FROM users WHERE mobile_number = :mobile"),
        {"mobile": data.mobile_number}
    ).fetchone()

    if user:
        user_id = user.id
    else:
        result = db.execute(
            text("""
                INSERT INTO users (name, mobile_number, city, is_active, created_at, updated_at)
                VALUES (:name, :mobile, :city, 1, NOW(), NOW())
            """),
            {
                "name": data.name,
                "mobile": data.mobile_number,
                "city": data.city
            }
        )
        db.commit()
        user_id = result.lastrowid

    db.commit()

    return {
        "success": True,
        "user_id": user_id,
        "message": "OTP verified successfully"
    }
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import booking, ticket, payment, scanner,auth,analytics

app = FastAPI(
    title="AbadhaBook API",
    description="Online Meal Ticket Booking System for Agara Shri Jagannatha Swamy Temple",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(booking.router, prefix="/api/booking", tags=["Booking"])
app.include_router(ticket.router, prefix="/api/ticket", tags=["Ticket"])
app.include_router(payment.router, prefix="/api/payment", tags=["Payment"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["Scanner"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])


@app.get("/")
def root():
    return {
        "message": "Welcome to AbadhaBook API 🛕",
        "temple": "Agara Shri Jagannatha Swamy Temple",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "api": "AbadhaBook"}

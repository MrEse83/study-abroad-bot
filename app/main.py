from fastapi import FastAPI
from app.database import Base, engine
from app.routers import patients, doctors, appointments, whatsapp

# Create all tables in Neon on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CliniQ",
    description="AI-powered clinic appointment system via WhatsApp",
    version="1.0.0"
)

# Register all routers
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(whatsapp.router)


@app.get("/")
def root():
    return {
        "app": "CliniQ",
        "status": "running",
        "message": "AI-powered clinic appointment system"
    }


@app.get("/health")
def health():
    return {"status": "ok"}

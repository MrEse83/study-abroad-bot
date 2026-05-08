from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.routers import whatsapp, dashboard

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Study Abroad Bot",
    description="AI-powered study abroad assistant via WhatsApp",
    version="1.0.0"
)

# Serve static files (dashboard UI)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routers
app.include_router(whatsapp.router)
app.include_router(dashboard.router)

@app.get("/")
def root():
    return {"app": "Study Abroad Bot", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}
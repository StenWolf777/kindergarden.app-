"""
Bog'chaOS REST API Server (FastAPI)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.routes import dashboard, children, attendance, billing, tabel, staff, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    init_db()
    print("[Bog'chaOS Backend] Malumotlar bazasi va jadvallar muvaffaqiyatli ishga tushirildi.")
    yield

app = FastAPI(
    title="Bog'chaOS Backend API",
    description="Xususiy bog'chalar uchun B2B SaaS platformasi REST API xizmati.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS sozlamalari (Frontend ulanishi uchun)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routerlarni ulash
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(children.router)
app.include_router(attendance.router)
app.include_router(billing.router)
app.include_router(tabel.router)
app.include_router(staff.router)

@app.get("/")
def root():
    return {
        "app": "Bog'chaOS SaaS API",
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

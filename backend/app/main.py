
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.employees import router as employees_router
from app.api.routes.salary import router as salary_router
from app.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.user import User


def ensure_default_users() -> None:
    db: Session = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(
                User(
                    username="admin",
                    email="admin@acme.local",
                    password_hash=hash_password("admin123"),
                    role="admin",
                )
            )
        if not db.query(User).filter(User.username == "hr_manager").first():
            db.add(
                User(
                    username="hr_manager",
                    email="hr_manager@acme.local",
                    password_hash=hash_password("hr123"),
                    role="hr_manager",
                )
            )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_default_users()
    yield


app = FastAPI(
    title="ACME Salary Management API",
    description="Local API for employee and salary management.",
    version="1.0.0",
    lifespan=lifespan,
)

frontend_origin = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:5173",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(employees_router, prefix="/employees", tags=["employees"])
app.include_router(salary_router, prefix="/salary", tags=["salary"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])


@app.get("/")
def root():
    return {"message": "ACME Salary Management API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}

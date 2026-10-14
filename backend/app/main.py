
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import Employee


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenient for initial local development.
    # Use Alembic migrations for ongoing schema changes.
    Base.metadata.create_all(bind=engine)
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


@app.get("/")
def root():
    return {"message": "ACME Salary Management API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}

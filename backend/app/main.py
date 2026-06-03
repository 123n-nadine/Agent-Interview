from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import jobs_router, interviews_router
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Interview Platform API")

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(interviews_router.router, prefix="/api/v1/interviews", tags=["Interviews"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Interview Platform API"}

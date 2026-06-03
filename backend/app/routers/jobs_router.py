from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas import JobResponse
from ..services.jobs_service import fetch_and_sync_jobs

router = APIRouter()

@router.get("/", response_model=List[JobResponse])
def get_jobs(db: Session = Depends(get_db)):
    jobs = fetch_and_sync_jobs(db)
    return jobs

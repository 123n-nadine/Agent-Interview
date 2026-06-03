import os
import requests
from sqlalchemy.orm import Session
from ..models import Job
import time

REVUP_JOBS_API = os.getenv("REVUP_JOBS_API", "https://revup-backend-production.up.railway.app/api/jobs")

_jobs_cache = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 600 # 10 minutes

def fetch_and_sync_jobs(db: Session):
    global _jobs_cache
    if _jobs_cache["data"] and (time.time() - _jobs_cache["timestamp"]) < CACHE_TTL:
        return _jobs_cache["data"]

    try:
        response = requests.get(REVUP_JOBS_API, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("success") or not data.get("data"):
            return _jobs_cache["data"] or []
            
        jobs_data = data["data"]
        synced_jobs = []
        
        for job_data in jobs_data:
            job = db.query(Job).filter(Job.revup_id == job_data["id"]).first()
            skills = [skill["name"] for skill in job_data.get("skills", [])]
            
            if not job:
                job = Job(
                    revup_id=job_data["id"],
                    title=job_data.get("title", ""),
                    description=job_data.get("description", ""),
                    skills=skills,
                    seniority=job_data.get("seniority", "Unspecified")
                )
                db.add(job)
            else:
                job.title = job_data.get("title", job.title)
                job.description = job_data.get("description", job.description)
                job.skills = skills
                
            synced_jobs.append(job)
            
        db.commit()
        _jobs_cache["data"] = synced_jobs
        _jobs_cache["timestamp"] = time.time()
        return synced_jobs
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        # Fallback to returning existing jobs from local DB if API fails
        db_jobs = db.query(Job).all()
        if not _jobs_cache["data"]:
            _jobs_cache["data"] = db_jobs
        return _jobs_cache["data"]

def get_job_by_id(db: Session, job_id: int):
    # Try to find in cache first
    if _jobs_cache["data"]:
        for j in _jobs_cache["data"]:
            if j.id == job_id:
                return j
    return db.query(Job).filter(Job.id == job_id).first()

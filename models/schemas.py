from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ResumeData(BaseModel):
    """Parsed resume data structure"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    experience_level: str = "entry"  # entry, mid, senior, executive
    job_titles: List[str] = []
    companies: List[str] = []
    education: List[str] = []
    certifications: List[str] = []
    keywords: List[str] = []
    years_of_experience: Optional[int] = None

class JobResult(BaseModel):
    """LinkedIn job result structure"""
    title: str
    company: str
    location: str
    description: str
    job_url: str
    posted_date: Optional[str] = None
    employment_type: Optional[str] = None  # Full-time, Part-time, Contract, etc.
    seniority_level: Optional[str] = None
    required_skills: List[str] = []
    match_score: float = 0.0  # 0-100 relevance score
    matched_keywords: List[str] = []

class SearchResponse(BaseModel):
    """API response structure"""
    resume_summary: ResumeData
    jobs: List[JobResult]
    total_found: int
    search_parameters: Dict[str, Any]
    timestamp: datetime = datetime.now()

class ErrorResponse(BaseModel):
    """Error response structure"""
    error: str
    message: str
    timestamp: datetime = datetime.now()

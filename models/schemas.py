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

class JobDescription(BaseModel):
    """Job description input structure"""
    title: str
    company: str
    description: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    experience_level: str = "mid"  # entry, mid, senior, executive
    location: str = "United States"
    employment_type: str = "Full-time"
    salary_range: Optional[str] = None

class CandidateProfile(BaseModel):
    """LinkedIn candidate profile structure"""
    name: str
    headline: str
    location: str
    profile_url: str
    current_position: Optional[str] = None
    company: Optional[str] = None
    skills: List[str] = []
    experience_level: str = "mid"
    education: List[str] = []
    is_open_to_work: bool = False
    summary: Optional[str] = None
    match_score: float = 0.0  # 0-100 relevance score
    matched_skills: List[str] = []
    years_of_experience: Optional[int] = None

class CandidateSearchRequest(BaseModel):
    """Request structure for candidate search"""
    job_description: JobDescription
    max_results: Optional[int] = 20
    location_radius: Optional[int] = 50  # miles

class CandidateSearchResponse(BaseModel):
    """API response structure for candidate search"""
    job_summary: JobDescription
    candidates: List[CandidateProfile]
    total_found: int
    search_parameters: Dict[str, Any]
    timestamp: datetime = datetime.now()

class SimpleCandidateSearchRequest(BaseModel):
    """Simplified request structure for candidate search with raw job description"""
    job_description_text: str
    company: Optional[str] = None
    max_results: Optional[int] = 20

class ErrorResponse(BaseModel):
    """Error response structure"""
    error: str
    message: str
    timestamp: datetime = datetime.now()

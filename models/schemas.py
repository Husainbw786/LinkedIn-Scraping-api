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

# New schemas for candidate finder functionality
class JobDescriptionInput(BaseModel):
    """Input schema for job description text"""
    job_description: str

class CandidateProfile(BaseModel):
    """Candidate profile structure from CrustData API"""
    name: str
    location: Optional[str] = None
    linkedin_profile_url: Optional[str] = None
    linkedin_profile_urn: Optional[str] = None
    default_position_title: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    num_of_connections: Optional[int] = None
    skills: List[str] = []
    current_title: Optional[str] = None
    profile_picture_url: Optional[str] = None
    employer: List[Dict[str, Any]] = []
    education_background: List[Dict[str, Any]] = []
    emails: List[str] = []
    websites: List[str] = []
    years_of_experience: Optional[str] = None
    match_score: float = 0.0
    match_explanation: Optional[str] = None

class CandidateSearchResponse(BaseModel):
    """Response structure for candidate search"""
    candidates: List[CandidateProfile]
    total_found: int
    search_filters: Dict[str, Any]
    extracted_keywords: List[str]
    timestamp: datetime = datetime.now()

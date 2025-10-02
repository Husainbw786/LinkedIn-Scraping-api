from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import re

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

# New schemas for resume matching functionality
class ResumeCandidate(BaseModel):
    """Resume candidate structure for matching"""
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    resume_url: str
    file_name: str
    skills: List[str] = []
    experience_years: int = 0
    job_titles: List[str] = []
    companies: List[str] = []
    education: List[str] = []
    summary: Optional[str] = None
    match_score: float = 0.0
    match_explanation: Optional[str] = None
    
    @field_validator('experience_years', mode='before')
    @classmethod
    def parse_experience_years(cls, v):
        """Convert experience years string to integer"""
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            # Extract numbers from strings like "5+", "3-5", "5 years", etc.
            numbers = re.findall(r'\d+', str(v))
            if numbers:
                # Take the first number found
                return int(numbers[0])
            # Handle text descriptions
            text_to_num = {
                'entry': 1, 'junior': 2, 'mid': 4, 'senior': 7, 'lead': 8, 'principal': 10
            }
            v_lower = v.lower()
            for key, num in text_to_num.items():
                if key in v_lower:
                    return num
        return 0

class ResumeCandidateSearchResponse(BaseModel):
    """Response structure for resume candidate search"""
    candidates: List[ResumeCandidate]
    total_found: int
    search_query: str
    search_time_ms: int = 0
    timestamp: datetime = datetime.now()

class ResumeIngestionResponse(BaseModel):
    """Response structure for resume ingestion"""
    success: bool
    total_files: int
    processed: int
    failed: int
    failed_files: List[Dict[str, str]] = []
    message: str
    timestamp: datetime = datetime.now()

class ResumeStatsResponse(BaseModel):
    """Response structure for resume statistics"""
    total_resumes: int
    index_dimension: int = 0
    index_fullness: float = 0.0
    status: str
    error: Optional[str] = None
    timestamp: datetime = datetime.now()

class SingleResumeUploadRequest(BaseModel):
    """Request structure for single resume upload"""
    google_drive_url: str
    file_name: Optional[str] = None  # Optional, will be extracted from URL if not provided

class SingleResumeUploadResponse(BaseModel):
    """Response structure for single resume upload"""
    success: bool
    resume_id: Optional[str] = None
    candidate_name: Optional[str] = None
    file_name: str
    message: str
    error: Optional[str] = None
    timestamp: datetime = datetime.now()

class FileUploadResponse(BaseModel):
    """Response structure for file upload"""
    success: bool
    resume_id: Optional[str] = None
    candidate_name: Optional[str] = None
    file_name: str
    file_size: int
    google_drive_url: Optional[str] = None
    message: str
    error: Optional[str] = None
    timestamp: datetime = datetime.now()

# New schemas for ATS scoring functionality
class ATSScoreRequest(BaseModel):
    """Request structure for ATS scoring"""
    resume_url: str
    job_description: Optional[str] = None

class CategoryScore(BaseModel):
    """Individual category score structure"""
    score: int
    feedback: str
    red_flags: List[str] = []

class JobAlignment(BaseModel):
    """Job-specific alignment analysis"""
    job_match_score: int
    relevant_skills_found: List[str] = []
    missing_critical_skills: List[str] = []
    experience_level_match: str
    job_specific_recommendations: List[str] = []

class ATSScoreResponse(BaseModel):
    """Response structure for ATS scoring"""
    overall_score: int
    category_scores: Dict[str, CategoryScore]
    summary: str
    recommendations: List[str]
    risk_level: str  # LOW, MEDIUM, HIGH
    confidence_score: int
    job_alignment: Optional[JobAlignment] = None
    parsing_note: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = datetime.now()

class ResumeExtractionResult(BaseModel):
    """Result of resume text extraction"""
    text: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

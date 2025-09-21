from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from utils.logger_config import setup_logging

# Setup logging
logger = setup_logging()

from services.resume_parser import ResumeParser
from services.linkedin_scraper import LinkedInScraper
from services.job_matcher import JobMatcher
from services.crustdata_api import CrustDataAPI
from services.job_description_parser import JobDescriptionParser
from services.candidate_matcher import CandidateMatcher
from models.schemas import JobResult, ResumeData, SearchResponse, JobDescriptionInput, CandidateSearchResponse, CandidateProfile

load_dotenv()

app = FastAPI(
    title="LinkedIn Job Scraper & Candidate Finder API",
    description="API that finds relevant LinkedIn jobs from resumes and finds candidates from job descriptions using CrustData",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
resume_parser = ResumeParser()
linkedin_scraper = LinkedInScraper()
job_matcher = JobMatcher()
crustdata_api = CrustDataAPI()
job_description_parser = JobDescriptionParser()
candidate_matcher = CandidateMatcher()

@app.post("/api/v1/search-jobs", response_model=SearchResponse)
async def search_jobs(
    file: UploadFile = File(...),
    location: Optional[str] = "United States",
    max_results: Optional[int] = 20
):
    """
    Upload resume PDF and get relevant LinkedIn job matches
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Parse resume
        logger.info(f"Processing resume: {file.filename}")
        resume_data = await resume_parser.parse_pdf(file)
        
        # Search LinkedIn jobs
        logger.info(f"Searching LinkedIn jobs for skills: {resume_data.skills[:5]}")
        raw_jobs = await linkedin_scraper.search_jobs(
            skills=resume_data.skills,
            experience_level=resume_data.experience_level,
            location=location,
            max_results=max_results
        )
        
        # Match and rank jobs
        matched_jobs = job_matcher.rank_jobs(resume_data, raw_jobs)
        
        return SearchResponse(
            resume_summary=resume_data,
            jobs=matched_jobs,
            total_found=len(matched_jobs),
            search_parameters={
                "location": location,
                "max_results": max_results,
                "skills_searched": resume_data.skills[:10]
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/api/v1/find-candidates", response_model=CandidateSearchResponse)
async def find_candidates(job_input: JobDescriptionInput):
    """
    Find candidates based on job description using CrustData API
    
    Takes a job description text and returns ranked candidates that match the requirements.
    The API automatically extracts job titles, skills, experience levels, and other relevant
    filters from the job description to search for suitable candidates.
    """
    try:
        logger.info("Processing candidate search request")
        
        # Parse job description to extract search criteria
        job_requirements = job_description_parser.parse_job_description(job_input.job_description)
        
        logger.info(f"Extracted job requirements: {job_requirements}")
        
        # Search for candidates using CrustData API
        search_results = await crustdata_api.search_candidates(
            job_titles=job_requirements.get('job_titles', []),
            functions=job_requirements.get('functions', []),
            keywords=job_requirements.get('skills', []),
            locations=job_requirements.get('location', []),
            experience_levels=job_requirements.get('experience_level', [])
        )
        
        # Format candidate profiles
        candidates = []
        for profile_data in search_results.get('profiles', []):
            formatted_profile = crustdata_api.format_candidate_profile(profile_data)
            if formatted_profile:  # Only add if formatting was successful
                candidates.append(formatted_profile)
        
        logger.info(f"Found {len(candidates)} candidates from CrustData API")
        
        # Rank candidates based on job requirements
        ranked_candidates = candidate_matcher.rank_candidates(candidates, job_requirements)
        
        # Convert to Pydantic models
        candidate_profiles = []
        for candidate in ranked_candidates:
            try:
                profile = CandidateProfile(**candidate)
                candidate_profiles.append(profile)
            except Exception as e:
                logger.warning(f"Error creating candidate profile: {str(e)}")
                continue
        
        return CandidateSearchResponse(
            candidates=candidate_profiles,
            total_found=len(candidate_profiles),
            search_filters={
                "job_titles": job_requirements.get('job_titles', []),
                "functions": job_requirements.get('functions', []),
                "skills": job_requirements.get('skills', []),
                "locations": job_requirements.get('location', []),
                "experience_levels": job_requirements.get('experience_level', [])
            },
            extracted_keywords=job_requirements.get('all_extracted_keywords', [])
        )
        
    except Exception as e:
        logger.error(f"Error processing candidate search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Candidate search error: {str(e)}")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LinkedIn Job Scraper & Candidate Finder API"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LinkedIn Job Scraper & Candidate Finder API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )

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
    Find candidates based on job description using OpenAI + CrustData API
    
    This endpoint uses OpenAI to intelligently parse the job description and generate
    optimal search filters for the CrustData API. No hardcoded parsing - the AI
    determines the best search strategy based on the specific job requirements.
    
    Features:
    - OpenAI-powered job description analysis
    - Intelligent filter generation for CrustData API
    - Automatic fallback to simplified search if needed
    - Candidate ranking based on job requirements
    """
    try:
        logger.info("🤖 Starting AI-powered candidate search")
        
        # Use OpenAI + CrustData API for intelligent candidate search
        search_results = await crustdata_api.search_candidates_from_job_description(
            job_input.job_description
        )
        
        # Extract parsing info and profiles
        parsing_info = search_results.get('parsing_info', {})
        profiles = search_results.get('profiles', [])
        
        logger.info(f"🎯 OpenAI Strategy: {parsing_info.get('search_strategy', 'Unknown')}")
        logger.info(f"📊 Found {len(profiles)} candidates from CrustData API")
        
        # Format candidate profiles
        candidates = []
        for profile_data in profiles:
            formatted_profile = crustdata_api.format_candidate_profile(profile_data)
            if formatted_profile:  # Only add if formatting was successful
                candidates.append(formatted_profile)
        
        # Create job requirements from OpenAI parsing for candidate ranking
        filters_used = parsing_info.get('filters_used', {})
        job_requirements = {
            'job_titles': filters_used.get('job_titles', []),
            'skills': filters_used.get('keywords', []),
            'experience_level': filters_used.get('experience_levels', []),
            'location': filters_used.get('locations', []),
            'all_extracted_keywords': filters_used.get('keywords', [])
        }
        
        # Rank candidates based on job requirements
        if candidates:
            logger.info("🏆 Ranking candidates based on job requirements")
            ranked_candidates = candidate_matcher.rank_candidates(candidates, job_requirements)
        else:
            ranked_candidates = []
        
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
                "job_titles": filters_used.get('job_titles', []),
                "functions": filters_used.get('functions', []),
                "skills": filters_used.get('keywords', []),
                "locations": filters_used.get('locations', []),
                "experience_levels": filters_used.get('experience_levels', []),
                "ai_strategy": parsing_info.get('search_strategy', 'OpenAI optimized search'),
                "filters_applied": parsing_info.get('total_filters_applied', 0)
            },
            extracted_keywords=filters_used.get('keywords', [])
        )
        
    except Exception as e:
        logger.error(f"Error processing AI-powered candidate search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI candidate search error: {str(e)}")

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

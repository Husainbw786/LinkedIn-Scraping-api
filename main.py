from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
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
from services.resume_manager import ResumeManager
from models.schemas import (
    JobResult, ResumeData, SearchResponse, JobDescriptionInput,
    CandidateSearchResponse, CandidateProfile, ResumeCandidate,
    ResumeCandidateSearchResponse
)

load_dotenv()

app = FastAPI(
    title="LinkedIn Job Scraper & AI-Powered Candidate Finder API",
    description="Comprehensive API for LinkedIn job scraping and candidate discovery using both CrustData API and resume vector search with OpenAI-powered analysis",
    version="2.0.0"
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
resume_manager = ResumeManager()

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
        logger.info(f"Processing resume: {file.filename}")
        
        # Read and parse resume
        file_content = await file.read()
        resume_data = resume_parser.parse_resume(file_content, file.filename)
        
        if not resume_data.skills:
            raise HTTPException(status_code=400, detail="Could not extract skills from resume")
        
        # Search for jobs
        jobs = await linkedin_scraper.search_jobs(
            skills=resume_data.skills[:5],  # Use top 5 skills
            location=location,
            max_results=max_results
        )
        
        # Match and rank jobs
        matched_jobs = job_matcher.rank_jobs(jobs, resume_data)
        
        logger.info(f"Found {len(matched_jobs)} relevant jobs")
        
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
    - **Now limited to 10 results instead of 20**
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
        logger.info(f"📊 Found {len(profiles)} candidates from CrustData API (limited to 10)")
        
        # Format candidate profiles
        candidates = []
        for profile_data in profiles:
            formatted_profile = crustdata_api.format_candidate_profile(profile_data)
            if formatted_profile:  # Only add if formatting was successful
                candidates.append(formatted_profile)
        
        # Rank candidates using our matching algorithm
        if candidates:
            ranked_candidates = candidate_matcher.rank_candidates(
                candidates, 
                job_input.job_description
            )
        else:
            ranked_candidates = []
        
        # Get filters used for transparency
        filters_used = parsing_info.get('filters_used', {})
        
        return CandidateSearchResponse(
            candidates=ranked_candidates,
            total_found=len(ranked_candidates),
            search_filters={
                "job_titles": filters_used.get('job_titles', []),
                "functions": filters_used.get('functions', []),
                "skills": filters_used.get('keywords', []),
                "locations": filters_used.get('locations', []),
                "experience_levels": filters_used.get('experience_levels', []),
                "ai_strategy": parsing_info.get('search_strategy', 'OpenAI optimized search'),
                "filters_applied": parsing_info.get('total_filters_applied', 0),
                "result_limit": 10  # New field to show the limit
            },
            extracted_keywords=filters_used.get('keywords', [])
        )
        
    except Exception as e:
        logger.error(f"Error processing AI-powered candidate search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI candidate search error: {str(e)}")

@app.post("/api/v1/match-resumes", response_model=ResumeCandidateSearchResponse)
async def match_resumes(job_input: JobDescriptionInput, top_k: Optional[int] = 10):
    """
    Find best matching candidates from resume database based on job description
    
    This endpoint uses semantic search to find the most relevant candidates:
    - Generates embedding for the job description
    - Performs vector similarity search in Pinecone
    - Returns ranked candidates with match scores and Google Drive links
    
    Features:
    - Semantic matching (finds relevant candidates even with different terminology)
    - Ranked results with match scores and explanations
    - Direct links to resume PDFs on Google Drive
    - Structured candidate information (skills, experience, etc.)
    """
    try:
        logger.info("🔍 Starting resume matching process")
        
        # Find matching candidates
        result = await resume_manager.find_matching_candidates(
            job_input.job_description, 
            top_k
        )
        
        return ResumeCandidateSearchResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in resume matching: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Resume matching error: {str(e)}")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LinkedIn Job Scraper & CrustData Candidate Finder API"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LinkedIn Job Scraper & CrustData Candidate Finder API", "docs": "/docs"}

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

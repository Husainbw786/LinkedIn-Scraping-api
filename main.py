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
from services.resume_fetcher import ResumeFetcher
from services.ats_scorer import ATSScorer
from models.schemas import (
    JobResult, ResumeData, SearchResponse, JobDescriptionInput,
    CandidateSearchResponse, CandidateProfile, ResumeCandidate,
    ResumeCandidateSearchResponse, ATSScoreRequest, ATSScoreResponse
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
resume_fetcher = ResumeFetcher()
ats_scorer = ATSScorer()

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
        
        # Parse resume directly from UploadFile
        resume_data = await resume_parser.parse_pdf(file)
        
        if not resume_data.skills:
            raise HTTPException(status_code=400, detail="Could not extract skills from resume")
        
        # Search for jobs
        jobs = await linkedin_scraper.search_jobs(
            skills=resume_data.skills[:5],  # Use top 5 skills
            location=location,
            max_results=max_results
        )
        
        # Match and rank jobs
        matched_jobs = job_matcher.rank_jobs(resume_data, jobs)
        
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
    - Direct links to resume PDFs on Google Drive (if available)
    - Structured candidate information (skills, experience, etc.)
    
    Note: Requires Pinecone to be configured. Google Drive is optional.
    """
    try:
        logger.info("🔍 Starting resume matching process")
        
        # Check if Google Drive is available
        if not resume_manager.drive_service.is_available:
            logger.warning("⚠️ Google Drive not available, but proceeding with Pinecone search")
        
        # Find matching candidates
        result = await resume_manager.find_matching_candidates(
            job_input.job_description, 
            top_k
        )
        
        return ResumeCandidateSearchResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in resume matching: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Resume matching error: {str(e)}")

@app.post("/api/v1/calculate-ats-score", response_model=ATSScoreResponse)
async def calculate_ats_score(request: ATSScoreRequest):
    """
    Calculate comprehensive ATS score for a resume from URL
    
    This endpoint analyzes resumes based on 7 critical criteria:
    1. Tech Stack Consistency (20%) - Logical technology combinations
    2. LinkedIn Authenticity & Alignment (15%) - Professional credibility
    3. Project Depth and Relevance (20%) - Detailed project descriptions
    4. Resume Length & Format Quality (10%) - Structure and presentation
    5. Duplicate or Template Content (15%) - Authenticity assessment
    6. Employment Timeline Coherence (10%) - Career progression logic
    7. Education and Certification Validation (10%) - Credential relevance
    
    Features:
    - Supports multiple resume formats (PDF, DOCX, Google Docs, HTML)
    - OpenAI GPT-4o powered analysis
    - Optional job-specific scoring when job description provided
    - Detailed feedback and improvement recommendations
    - Risk assessment and confidence scoring
    
    Note: Requires OpenAI API key to be configured.
    """
    try:
        logger.info(f"🎯 Starting ATS score calculation for URL: {request.resume_url}")
        
        # Step 1: Fetch and extract resume text
        extraction_result = await resume_fetcher.fetch_resume_text(request.resume_url)
        
        if not extraction_result.success:
            logger.error(f"Failed to extract resume text: {extraction_result.error}")
            raise HTTPException(
                status_code=400, 
                detail=f"Could not extract resume content: {extraction_result.error}"
            )
        
        if len(extraction_result.text.strip()) < 100:
            raise HTTPException(
                status_code=400,
                detail="Resume content is too short or empty. Please ensure the URL points to a valid resume document."
            )
        
        logger.info(f"✅ Successfully extracted {len(extraction_result.text)} characters from resume")
        
        # Step 2: Calculate ATS score using OpenAI
        ats_result = await ats_scorer.calculate_ats_score(
            extraction_result.text, 
            request.job_description
        )
        
        # Step 3: Format response
        from models.schemas import CategoryScore, JobAlignment
        
        # Convert category scores to proper format
        formatted_categories = {}
        for category, data in ats_result.get('category_scores', {}).items():
            formatted_categories[category] = CategoryScore(
                score=data.get('score', 0),
                feedback=data.get('feedback', ''),
                red_flags=data.get('red_flags', [])
            )
        
        # Handle job alignment if present
        job_alignment = None
        if 'job_alignment' in ats_result and ats_result['job_alignment']:
            job_data = ats_result['job_alignment']
            job_alignment = JobAlignment(
                job_match_score=job_data.get('job_match_score', 0),
                relevant_skills_found=job_data.get('relevant_skills_found', []),
                missing_critical_skills=job_data.get('missing_critical_skills', []),
                experience_level_match=job_data.get('experience_level_match', 'Unknown'),
                job_specific_recommendations=job_data.get('job_specific_recommendations', [])
            )
        
        response = ATSScoreResponse(
            overall_score=ats_result.get('overall_score', 0),
            category_scores=formatted_categories,
            summary=ats_result.get('summary', ''),
            recommendations=ats_result.get('recommendations', []),
            risk_level=ats_result.get('risk_level', 'MEDIUM'),
            confidence_score=ats_result.get('confidence_score', 0),
            job_alignment=job_alignment,
            parsing_note=ats_result.get('parsing_note'),
            error=ats_result.get('error')
        )
        
        logger.info(f"🎉 ATS scoring completed. Overall score: {response.overall_score}/100")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in ATS scoring: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ATS scoring error: {str(e)}")

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

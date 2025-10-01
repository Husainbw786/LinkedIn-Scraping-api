from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
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
    ResumeCandidateSearchResponse, ResumeIngestionResponse, ResumeStatsResponse,
    SingleResumeUploadRequest, SingleResumeUploadResponse, FileUploadResponse
)

load_dotenv()

app = FastAPI(
    title="AI-Powered Resume Matching & Candidate Finder API",
    description="Comprehensive API for resume matching and candidate discovery using AI embeddings, vector search, and multiple data sources including Google Drive and CrustData",
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

@app.post("/api/v1/ingest-resumes", response_model=ResumeIngestionResponse)
async def ingest_resumes(background_tasks: BackgroundTasks):
    """
    Ingest all resumes from Google Drive folder into Pinecone vector database
    
    This endpoint processes all PDF resumes in the configured Google Drive folder:
    - Downloads PDFs from Google Drive
    - Extracts and parses resume content using OpenAI
    - Generates embeddings for semantic search
    - Stores in Pinecone with metadata including Google Drive URLs
    
    The process runs in the background for large folders.
    """
    try:
        logger.info("🚀 Starting resume ingestion process")
        
        # Run ingestion process
        result = await resume_manager.ingest_all_resumes()
        
        return ResumeIngestionResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in resume ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Resume ingestion error: {str(e)}")

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

@app.get("/api/v1/resume-stats", response_model=ResumeStatsResponse)
async def get_resume_stats():
    """
    Get statistics about the resume database
    
    Returns information about:
    - Total number of resumes stored
    - Database health status
    - Index statistics
    """
    try:
        stats = await resume_manager.get_resume_stats()
        return ResumeStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting resume stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")

@app.delete("/api/v1/clear-resumes")
async def clear_all_resumes():
    """
    Clear all resumes from the database (use with caution!)
    
    This endpoint will delete all resume data from Pinecone.
    Use this for testing or when you want to start fresh.
    """
    try:
        logger.warning(" Clearing all resumes from database")
        result = await resume_manager.delete_all_resumes()
        return result
    except Exception as e:
        logger.error(f"Error clearing resumes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Clear error: {str(e)}")

@app.post("/api/v1/upload-single-resume", response_model=SingleResumeUploadResponse)
async def upload_single_resume(request: SingleResumeUploadRequest):
    """
    Upload a single resume from Google Drive URL to Pinecone
    
    This endpoint allows you to upload individual resumes by providing:
    - Google Drive shareable URL (required)
    - Optional file name (will be extracted from URL if not provided)
    
    Supported formats: PDF, DOCX, DOC
    
    Example URLs:
    - https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    - https://drive.google.com/open?id=FILE_ID
    - https://docs.google.com/document/d/FILE_ID/edit
    """
    try:
        logger.info(f" Single resume upload request: {request.google_drive_url}")
        result = await resume_manager.upload_single_resume_by_url(
            request.google_drive_url,
            request.file_name
        )
        return SingleResumeUploadResponse(**result)
    except Exception as e:
        logger.error(f"Error in single resume upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

@app.post("/api/v1/upload-resume-file", response_model=FileUploadResponse)
async def upload_resume_file(
    file: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    google_drive_url: Optional[str] = Form(None, description="Optional Google Drive URL for reference")
):
    """
    Upload a resume file directly with optional Google Drive URL
    
    This endpoint allows you to upload resume files directly:
    - Upload PDF or DOCX files
    - Optionally provide Google Drive URL for reference
    - Same AI processing as other endpoints
    
    Supported formats: PDF, DOCX, DOC
    Max file size: 10MB
    """
    try:
        logger.info(f"📤 File upload request: {file.filename}")
        
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        supported_extensions = ['.pdf', '.docx', '.doc']
        if not any(file.filename.lower().endswith(ext) for ext in supported_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Only {', '.join(supported_extensions)} files are supported."
            )
        
        # Read file content
        file_content = await file.read()
        
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
            )
        
        logger.info(f"📄 Processing uploaded file: {file.filename} ({len(file_content)} bytes)")
        
        # Process the resume
        result = await resume_manager.upload_resume_from_file(
            file_content,
            file.filename,
            google_drive_url
        )
        
        return FileUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in file upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload error: {str(e)}")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LinkedIn Job Scraper & Candidate Finder API"}
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

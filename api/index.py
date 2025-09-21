from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import tempfile
import asyncio
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logger_config import setup_logging
from services.resume_parser import ResumeParser
from services.linkedin_scraper import LinkedInScraper
from services.job_matcher import JobMatcher
from services.candidate_scraper import LinkedInCandidateScaper
from services.candidate_matcher import CandidateMatcher
from services.openai_parser import OpenAIJobParser
from models.schemas import JobResult, ResumeData, SearchResponse, JobDescription, CandidateSearchRequest, CandidateSearchResponse, SimpleCandidateSearchRequest

# Setup logging
logger = setup_logging()

app = FastAPI(
    title="LinkedIn Job Scraper & Candidate Finder API",
    description="API that finds relevant LinkedIn jobs for resumes AND finds qualified candidates for job descriptions",
    version="1.1.0"
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
candidate_scraper = LinkedInCandidateScaper()
candidate_matcher = CandidateMatcher()
openai_parser = OpenAIJobParser()

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
async def find_candidates(request: CandidateSearchRequest):
    """
    Find and rank candidates based on job description
    """
    try:
        job_desc = request.job_description
        max_results = request.max_results or 20
        
        logger.info(f"Searching candidates for job: {job_desc.title} at {job_desc.company}")
        
        # Extract skills from job description if not provided
        if not job_desc.required_skills and not job_desc.preferred_skills:
            # Simple skill extraction from description
            all_skills = _extract_skills_from_description(job_desc.description)
            job_desc.required_skills = all_skills[:5]  # Top 5 as required
            job_desc.preferred_skills = all_skills[5:10]  # Next 5 as preferred
        
        # Search for candidates
        all_skills = job_desc.required_skills + job_desc.preferred_skills
        logger.info(f"Searching candidates with skills: {all_skills[:5]}")
        
        raw_candidates = await candidate_scraper.search_candidates(
            skills=all_skills,
            job_title=job_desc.title,
            location=job_desc.location,
            experience_level=job_desc.experience_level,
            max_results=max_results
        )
        
        # Rank candidates based on job requirements
        ranked_candidates = candidate_matcher.rank_candidates(job_desc, raw_candidates)
        
        return CandidateSearchResponse(
            job_summary=job_desc,
            candidates=ranked_candidates,
            total_found=len(ranked_candidates),
            search_parameters={
                "location": job_desc.location,
                "max_results": max_results,
                "experience_level": job_desc.experience_level,
                "skills_searched": all_skills[:10],
                "note": "⚠️ DEMO MODE: Currently showing realistic mock profiles for demonstration. In production, this would return real LinkedIn candidate data."
            }
        )
        
    except Exception as e:
        logger.error(f"Error finding candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Candidate search error: {str(e)}")

@app.post("/api/v1/find-candidates-simple", response_model=CandidateSearchResponse)
async def find_candidates_simple(request: SimpleCandidateSearchRequest):
    """
    🆕 SIMPLIFIED: Find candidates by just pasting job description text!
    
    This endpoint takes raw job description text and automatically extracts:
    - Job title, required skills, preferred skills
    - Experience level, location, employment type
    - Then finds and ranks matching candidates
    
    Much easier than the structured endpoint - just paste the JD and go!
    """
    try:
        job_text = request.job_description_text
        company = request.company
        max_results = request.max_results or 20
        
        logger.info(f"Parsing job description text ({len(job_text)} chars) for company: {company or 'Unknown'}")
        
        # Parse job description using OpenAI or fallback
        job_desc = await openai_parser.parse_job_description(job_text, company)
        
        logger.info(f"Parsed job: {job_desc.title} | Skills: {job_desc.required_skills[:3]}")
        
        # Search for candidates using the parsed job description
        all_skills = job_desc.required_skills + job_desc.preferred_skills
        
        logger.info(f"Searching for candidates with skills: {all_skills}")
        raw_candidates = await candidate_scraper.search_candidates(
            skills=all_skills,
            job_title=job_desc.title,
            location=job_desc.location,
            experience_level=job_desc.experience_level,
            max_results=max_results
        )
        logger.info(f"Found {len(raw_candidates)} raw candidates")
        
        # Rank candidates based on job requirements
        ranked_candidates = candidate_matcher.rank_candidates(job_desc, raw_candidates)
        
        return CandidateSearchResponse(
            job_summary=job_desc,
            candidates=ranked_candidates,
            total_found=len(ranked_candidates),
            search_parameters={
                "location": job_desc.location,
                "max_results": max_results,
                "experience_level": job_desc.experience_level,
                "skills_searched": all_skills[:10],
                "parsing_method": "openai" if openai_parser.use_openai else "fallback",
                "note": "⚠️ DEMO MODE: Currently showing realistic mock profiles for demonstration. In production, this would return real LinkedIn candidate data."
            }
        )
        
    except Exception as e:
        logger.error(f"Error in simplified candidate search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Simplified candidate search error: {str(e)}")

def _extract_skills_from_description(description: str) -> List[str]:
    """Extract technical skills from job description"""
    # Common technical skills to look for
    common_skills = [
        "Python", "JavaScript", "Java", "C++", "C#", "Go", "Rust", "TypeScript",
        "React", "Angular", "Vue.js", "Node.js", "Express", "Django", "Flask",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "Git",
        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "Machine Learning", "Data Science", "AI", "Deep Learning", "TensorFlow",
        "PyTorch", "Pandas", "NumPy", "Scikit-learn", "Apache Spark",
        "DevOps", "CI/CD", "Terraform", "Ansible", "Linux", "Unix",
        "REST API", "GraphQL", "Microservices", "Agile", "Scrum", "Jira"
    ]
    
    found_skills = []
    description_lower = description.lower()
    
    for skill in common_skills:
        if skill.lower() in description_lower:
            found_skills.append(skill)
    
    return found_skills

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LinkedIn Job Scraper API"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LinkedIn Job Scraper & Candidate Finder API", 
        "docs": "/docs",
        "endpoints": {
            "search_jobs": "/api/v1/search-jobs",
            "find_candidates": "/api/v1/find-candidates",
            "find_candidates_simple": "/api/v1/find-candidates-simple",
            "health": "/api/v1/health"
        }
    }

# Export the app for Vercel
# This is the main entry point for Vercel
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

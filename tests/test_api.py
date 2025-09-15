import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import io
from pathlib import Path

from main import app
from models.schemas import ResumeData, JobResult

client = TestClient(app)

@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing"""
    # Create a simple text file that mimics a PDF
    content = b"Sample PDF content for testing"
    return ("test_resume.pdf", io.BytesIO(content), "application/pdf")

@pytest.fixture
def sample_resume_data():
    """Sample resume data for testing"""
    return ResumeData(
        name="John Doe",
        email="john.doe@example.com",
        skills=["Python", "React", "AWS", "Docker"],
        experience_level="senior",
        job_titles=["Software Engineer", "Senior Developer"],
        years_of_experience=5,
        keywords=["api", "microservices", "agile"]
    )

@pytest.fixture
def sample_jobs():
    """Sample job results for testing"""
    return [
        JobResult(
            title="Senior Python Developer",
            company="Tech Corp",
            location="San Francisco, CA",
            description="Looking for experienced Python developer with AWS knowledge",
            job_url="https://linkedin.com/jobs/123",
            match_score=85.5,
            matched_keywords=["Python", "AWS"]
        ),
        JobResult(
            title="React Frontend Developer",
            company="StartupXYZ",
            location="Remote",
            description="Frontend developer needed for React applications",
            job_url="https://linkedin.com/jobs/456",
            match_score=72.3,
            matched_keywords=["React"]
        )
    ]

class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Test health endpoint returns correct response"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

class TestJobSearchEndpoint:
    """Test job search endpoint"""
    
    @patch('services.resume_parser.ResumeParser.parse_pdf')
    @patch('services.linkedin_scraper.LinkedInScraper.search_jobs')
    @patch('services.job_matcher.JobMatcher.rank_jobs')
    def test_search_jobs_success(self, mock_rank_jobs, mock_search_jobs, mock_parse_pdf, 
                                sample_pdf_file, sample_resume_data, sample_jobs):
        """Test successful job search"""
        # Setup mocks
        mock_parse_pdf.return_value = sample_resume_data
        mock_search_jobs.return_value = sample_jobs
        mock_rank_jobs.return_value = sample_jobs
        
        # Make request
        response = client.post(
            "/api/v1/search-jobs",
            files={"file": sample_pdf_file},
            data={"location": "San Francisco", "max_results": "10"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert "resume_summary" in data
        assert "jobs" in data
        assert "total_found" in data
        assert data["total_found"] == 2
        assert len(data["jobs"]) == 2
        
        # Check job data
        job = data["jobs"][0]
        assert job["title"] == "Senior Python Developer"
        assert job["company"] == "Tech Corp"
        assert job["match_score"] == 85.5
    
    def test_search_jobs_invalid_file_type(self):
        """Test rejection of non-PDF files"""
        # Create a non-PDF file
        file_content = ("test.txt", io.BytesIO(b"Not a PDF"), "text/plain")
        
        response = client.post(
            "/api/v1/search-jobs",
            files={"file": file_content}
        )
        
        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]
    
    def test_search_jobs_no_file(self):
        """Test request without file"""
        response = client.post("/api/v1/search-jobs")
        assert response.status_code == 422  # Validation error
    
    @patch('services.resume_parser.ResumeParser.parse_pdf')
    def test_search_jobs_parsing_error(self, mock_parse_pdf, sample_pdf_file):
        """Test handling of resume parsing errors"""
        mock_parse_pdf.side_effect = ValueError("Failed to parse PDF")
        
        response = client.post(
            "/api/v1/search-jobs",
            files={"file": sample_pdf_file}
        )
        
        assert response.status_code == 500
        assert "Processing error" in response.json()["detail"]

class TestResumeParser:
    """Test resume parser functionality"""
    
    @pytest.mark.asyncio
    async def test_parse_pdf_basic(self):
        """Test basic PDF parsing"""
        from services.resume_parser import ResumeParser
        
        parser = ResumeParser()
        
        # Mock file upload
        mock_file = Mock()
        mock_file.read = asyncio.coroutine(lambda: b"John Doe\njohn@example.com\nPython Developer\n5 years experience")
        
        with patch.object(parser, '_extract_text_pypdf2', return_value="John Doe\njohn@example.com\nPython Developer\n5 years experience"):
            result = await parser.parse_pdf(mock_file)
            
            assert isinstance(result, ResumeData)
            assert result.name == "John Doe"
            assert result.email == "john@example.com"

class TestJobMatcher:
    """Test job matching functionality"""
    
    def test_rank_jobs(self, sample_resume_data, sample_jobs):
        """Test job ranking algorithm"""
        from services.job_matcher import JobMatcher
        
        matcher = JobMatcher()
        ranked_jobs = matcher.rank_jobs(sample_resume_data, sample_jobs)
        
        assert len(ranked_jobs) == 2
        assert ranked_jobs[0].match_score >= ranked_jobs[1].match_score
        assert all(job.match_score > 0 for job in ranked_jobs)
    
    def test_skills_matching(self):
        """Test skills matching logic"""
        from services.job_matcher import JobMatcher
        
        matcher = JobMatcher()
        
        resume_skills = ["Python", "AWS", "Docker"]
        job = JobResult(
            title="Python Developer",
            company="Test Corp",
            location="Remote",
            description="Looking for Python developer with AWS and Docker experience",
            job_url="https://example.com"
        )
        
        score = matcher._calculate_skills_match(resume_skills, job)
        assert score > 80  # Should be high match

class TestLinkedInScraper:
    """Test LinkedIn scraper functionality"""
    
    @pytest.mark.asyncio
    async def test_search_jobs_basic(self):
        """Test basic job search functionality"""
        from services.linkedin_scraper import LinkedInScraper
        
        scraper = LinkedInScraper()
        
        # Mock the scraping methods
        with patch.object(scraper, '_search_with_requests', return_value=[]):
            with patch.object(scraper, '_search_with_selenium', return_value=[]):
                jobs = await scraper.search_jobs(
                    skills=["Python"],
                    location="Remote",
                    max_results=5
                )
                
                assert isinstance(jobs, list)

class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self, sample_resume_data, sample_jobs):
        """Test full pipeline with mocked components"""
        with patch('services.resume_parser.ResumeParser.parse_pdf', return_value=sample_resume_data):
            with patch('services.linkedin_scraper.LinkedInScraper.search_jobs', return_value=sample_jobs):
                with patch('services.job_matcher.JobMatcher.rank_jobs', return_value=sample_jobs):
                    
                    file_content = ("test.pdf", io.BytesIO(b"PDF content"), "application/pdf")
                    
                    response = client.post(
                        "/api/v1/search-jobs",
                        files={"file": file_content},
                        data={"max_results": "5"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_found"] == 2

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

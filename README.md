# LinkedIn Job Scraper & Candidate Finder API

A comprehensive FastAPI-based service that provides two main functionalities:
1. **Job Finder**: Takes resume PDFs as input and finds relevant job opportunities on LinkedIn
2. **Candidate Finder**: Takes job descriptions as input and finds suitable candidates using CrustData API

The system intelligently parses content, extracts relevant information, and provides ranked results using advanced matching algorithms.

## Features

### Job Finder
- **Resume PDF Parsing**: Extract skills, experience, education, and keywords from PDF resumes
- **LinkedIn Job Scraping**: Multi-strategy scraping with anti-detection measures
- **Intelligent Job Matching**: ML-based ranking algorithm using TF-IDF similarity

### Candidate Finder (NEW)
- **Job Description Parsing**: Extract job titles, skills, experience requirements from text
- **CrustData Integration**: Search for candidates using professional database
- **Smart Candidate Matching**: Weighted scoring system for candidate ranking
- **Automatic Keyword Extraction**: AI-powered extraction of relevant search terms

### Common Features
- **Rate Limiting**: Built-in delays and retry logic to avoid detection
- **RESTful API**: Clean FastAPI endpoints with automatic documentation
- **Comprehensive Logging**: Structured logging with rotation and error tracking

## Architecture

```
├── main.py                          # FastAPI application entry point
├── models/
│   └── schemas.py                  # Pydantic data models
├── services/
│   ├── resume_parser.py            # PDF parsing and text extraction
│   ├── linkedin_scraper.py         # LinkedIn job scraping
│   ├── job_matcher.py              # Job ranking and matching
│   ├── crustdata_api.py            # CrustData API integration (NEW)
│   ├── job_description_parser.py   # Job description parsing (NEW)
│   └── candidate_matcher.py        # Candidate ranking algorithm (NEW)
├── utils/
│   ├── logger_config.py            # Logging configuration
│   └── exceptions.py               # Custom exceptions
└── tests/
    └── test_api.py                 # API testing suite
```

## Installation

1. **Clone and setup environment**:
```bash
cd /Users/husain_bw/consultadd/linked_job_scrapper
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Download NLTK data** (first run):
```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
```

## Usage

### Start the API Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### API Endpoints

#### POST `/api/v1/search-jobs`

Upload a resume PDF and get relevant LinkedIn job matches.

**Parameters**:
- `file`: Resume PDF file (multipart/form-data)
- `location`: Job search location (optional, default: "United States")
- `max_results`: Maximum number of jobs to return (optional, default: 20)

**Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/search-jobs" \
  -F "file=@resume.pdf" \
  -F "location=San Francisco, CA" \
  -F "max_results=10"
```

**Response**:
```json
{
  "resume_summary": {
    "name": "John Doe",
    "skills": ["Python", "React", "AWS"],
    "experience_level": "senior",
    "years_of_experience": 5
  },
  "jobs": [
    {
      "title": "Senior Python Developer",
      "company": "Tech Corp",
      "location": "San Francisco, CA",
      "description": "We are looking for...",
      "job_url": "https://linkedin.com/jobs/...",
      "match_score": 87.5,
      "matched_keywords": ["Python", "AWS", "API"]
    }
  ],
  "total_found": 15,
  "search_parameters": {
    "location": "San Francisco, CA",
    "max_results": 10
  }
}
```

#### POST `/api/v1/find-candidates` (NEW)

Find candidates based on job description using CrustData API.

**Parameters**:
- `job_description`: Job description text (JSON body)

**Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/find-candidates" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "We are looking for a Senior Backend Engineer with 5+ years of experience in Python, Django, AWS, and microservices. The ideal candidate should have experience with PostgreSQL, Redis, and Docker. Location: San Francisco, CA, United States."
  }'
```

**Response**:
```json
{
  "candidates": [
    {
      "name": "John Smith",
      "location": "San Francisco, CA, United States",
      "linkedin_profile_url": "https://www.linkedin.com/in/john-smith-engineer",
      "current_title": "Senior Backend Engineer",
      "headline": "Senior Backend Engineer | Python & AWS Expert",
      "summary": "Experienced Software Engineer with expertise in scalable systems...",
      "skills": ["Python", "Django", "AWS", "PostgreSQL", "Docker", "Redis"],
      "years_of_experience": "6 to 10 years",
      "match_score": 92.5,
      "match_explanation": "Skills match: 6/6 required skills; Title match: 'Senior Backend Engineer' vs required titles; Experience match: 6 to 10 years vs required levels; Location match: San Francisco, CA"
    }
  ],
  "total_found": 15,
  "search_filters": {
    "job_titles": ["Senior Backend Engineer", "Backend Engineer"],
    "functions": ["Engineering", "Information Technology"],
    "skills": ["Python", "Django", "AWS", "PostgreSQL", "Redis", "Docker"],
    "locations": ["San Francisco, CA, United States"],
    "experience_levels": ["6 to 10 years", "More than 10 years"]
  },
  "extracted_keywords": ["python", "django", "aws", "microservices", "postgresql", "redis", "docker"]
}
```

#### GET `/api/v1/health`

Health check endpoint.

## Configuration

### Environment Variables

```env
# LinkedIn Scraping
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

# CrustData API (NEW)
CRUSTDATA_API_TOKEN=your_crustdata_api_token_here

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Rate Limiting
REQUESTS_PER_MINUTE=30
SCRAPING_DELAY=2

# File Upload
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=./uploads

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

## How It Works

### 1. Resume Parsing
- Extracts text from PDF using PyPDF2 and pdfplumber
- Uses NLTK for text processing and keyword extraction
- Identifies skills from comprehensive database
- Determines experience level and job titles
- Extracts contact information and education

### 2. LinkedIn Scraping
- **Dual Strategy**: Requests-based scraping + Selenium fallback
- **Anti-Detection**: Random delays, rotating user agents, stealth headers
- **Rate Limiting**: Configurable delays between requests
- **Error Handling**: Retry logic with exponential backoff

### 3. Job Matching Algorithm
Weighted scoring system:
- **Skills Match (40%)**: Direct skill matching in job descriptions
- **Title Match (25%)**: Job title similarity to resume experience
- **Description Similarity (20%)**: TF-IDF cosine similarity
- **Experience Level (10%)**: Seniority level matching
- **Keyword Match (5%)**: General keyword overlap

### 4. Candidate Matching Algorithm (NEW)
Advanced weighted scoring system for candidate ranking:
- **Skills Match (40%)**: Required vs preferred skills matching
- **Title Match (25%)**: Job title alignment with candidate's current role
- **Experience Level (15%)**: Years of experience matching
- **Summary Similarity (10%)**: TF-IDF based content similarity
- **Location Match (10%)**: Geographic preference alignment

### 5. Job Description Parsing (NEW)
Intelligent extraction of search criteria:
- **Job Titles**: Pattern recognition for role identification
- **Technical Skills**: Comprehensive skill database matching
- **Experience Requirements**: Natural language processing for experience levels
- **Location Extraction**: Geographic information parsing
- **Keyword Extraction**: TF-IDF based important term identification

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Test specific endpoint
python tests/test_api.py

# Load testing
python tests/load_test.py
```

## Deployment

### Local Development
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Docker)
```bash
docker build -t linkedin-scraper .
docker run -p 8000:8000 linkedin-scraper
```

### Cloud Deployment
- **AWS**: Use ECS/Fargate with Application Load Balancer
- **GCP**: Deploy to Cloud Run or GKE
- **Azure**: Use Container Instances or AKS

## Rate Limiting & Ethics

This scraper implements responsible scraping practices:
- Configurable delays between requests (default: 2-4 seconds)
- Respect for robots.txt (where applicable)
- User-agent rotation and stealth headers
- Retry logic with exponential backoff
- No aggressive parallel requests

**Important**: Always comply with LinkedIn's Terms of Service and applicable laws.

## Troubleshooting

### Common Issues

1. **PDF Parsing Fails**:
   - Ensure PDF is text-based (not scanned image)
   - Check file size limits
   - Verify PDF is not password-protected

2. **LinkedIn Scraping Issues**:
   - Check internet connection
   - Verify Chrome/ChromeDriver installation
   - Adjust scraping delays in .env
   - Monitor for rate limiting

3. **Low Match Scores**:
   - Ensure resume contains relevant technical skills
   - Check job search location and keywords
   - Verify resume format is readable

### Logs

Check application logs:
```bash
tail -f logs/app.log      # General logs
tail -f logs/errors.log   # Error logs only
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit pull request

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is for educational and personal use only. Users are responsible for complying with LinkedIn's Terms of Service and applicable laws regarding web scraping.
# LinkedIn-api

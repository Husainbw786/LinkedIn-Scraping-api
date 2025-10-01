# 🎯 AI-Powered Resume Matching System

This system provides intelligent resume matching using vector embeddings and semantic search to find the best candidates for job descriptions.

## 🚀 Features

- **Semantic Resume Matching**: Uses OpenAI embeddings for intelligent candidate matching
- **Google Drive Integration**: Automatically processes resumes from Google Drive folders
- **Vector Database**: Powered by Pinecone for fast similarity search
- **AI-Powered Parsing**: OpenAI extracts structured data from resumes
- **Scalable Architecture**: Handles hundreds of resumes efficiently
- **RESTful API**: Easy integration with existing systems

## 🏗️ Architecture

```
Google Drive PDFs → Resume Parser → OpenAI Embeddings → Pinecone Vector DB
                                                              ↓
Job Description → OpenAI Embeddings → Vector Search → Ranked Candidates
```

## 📋 Prerequisites

1. **OpenAI API Key**: For embeddings and resume parsing
2. **Pinecone Account**: For vector database storage
3. **Google Cloud Project**: With Drive API enabled
4. **Service Account**: For Google Drive access

## ⚙️ Setup Instructions

### 1. Environment Variables

Add to your `.env` file:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=gcp-starter
PINECONE_INDEX_NAME=resume-matcher

# Google Drive API Configuration
GOOGLE_DRIVE_CREDENTIALS_PATH=./credentials/google-drive-credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id
```

### 2. Google Drive Setup

1. Create a Google Cloud Project
2. Enable Google Drive API
3. Create a Service Account
4. Download the JSON credentials file
5. Place it at `./credentials/google-drive-credentials.json`
6. Share your Google Drive folder with the service account email

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 🔧 API Endpoints

### 1. Ingest Resumes
```http
POST /api/v1/ingest-resumes
```

Processes all PDF resumes from the configured Google Drive folder and stores them in Pinecone.

**Response:**
```json
{
  "success": true,
  "total_files": 50,
  "processed": 48,
  "failed": 2,
  "message": "Successfully processed 48 out of 50 resumes"
}
```

### 2. Match Candidates
```http
POST /api/v1/match-resumes
Content-Type: application/json

{
  "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in Django, REST APIs, and cloud platforms like AWS. The candidate should have experience with databases, testing, and agile methodologies."
}
```

**Response:**
```json
{
  "candidates": [
    {
      "id": "resume_abc123_def456",
      "name": "John Doe",
      "email": "john.doe@email.com",
      "phone": "+1-555-0123",
      "resume_url": "https://drive.google.com/file/d/xyz/view",
      "file_name": "John_Doe_Resume.pdf",
      "skills": ["Python", "Django", "AWS", "PostgreSQL", "REST APIs"],
      "experience_years": 6,
      "job_titles": ["Senior Python Developer", "Backend Engineer"],
      "companies": ["TechCorp", "StartupXYZ"],
      "education": ["BS Computer Science - MIT"],
      "summary": "Experienced Python developer with expertise in web applications...",
      "match_score": 89.5,
      "match_explanation": "Excellent match - Strong alignment with job requirements"
    }
  ],
  "total_found": 12,
  "search_query": "We are looking for a Senior Python Developer...",
  "search_time_ms": 45
}
```

### 3. Resume Statistics
```http
GET /api/v1/resume-stats
```

**Response:**
```json
{
  "total_resumes": 48,
  "index_dimension": 1536,
  "index_fullness": 0.02,
  "status": "healthy"
}
```

### 4. Clear Database (Use with caution!)
```http
DELETE /api/v1/clear-resumes
```

## 🎯 How It Works

### Resume Processing Pipeline

1. **PDF Download**: Fetches PDFs from Google Drive
2. **Text Extraction**: Uses pdfplumber and PyPDF2 for robust text extraction
3. **AI Parsing**: OpenAI extracts structured data (name, skills, experience, etc.)
4. **Embedding Generation**: Creates vector embeddings using OpenAI's text-embedding-ada-002
5. **Storage**: Stores embeddings and metadata in Pinecone

### Candidate Matching Process

1. **Job Analysis**: Generates embedding for the job description
2. **Vector Search**: Performs cosine similarity search in Pinecone
3. **Ranking**: Scores candidates based on semantic similarity
4. **Response**: Returns ranked candidates with Google Drive links

## 📊 Match Scoring

- **90-100%**: Excellent match - Strong alignment with job requirements
- **80-89%**: Very good match - Most requirements align well
- **70-79%**: Good match - Several key requirements match
- **60-69%**: Moderate match - Some relevant experience
- **Below 60%**: Basic match - Limited alignment with requirements

## 🔍 Example Use Cases

### Use Case 1: Tech Startup Hiring
```bash
curl -X POST "http://localhost:8000/api/v1/match-resumes" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Looking for a Full Stack Developer with React, Node.js, and MongoDB experience. Should have startup experience and be comfortable with rapid development cycles."
  }'
```

### Use Case 2: Enterprise Role
```bash
curl -X POST "http://localhost:8000/api/v1/match-resumes" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Senior Data Scientist position requiring PhD in Statistics/CS, 8+ years experience with Python, R, machine learning, and big data technologies like Spark and Hadoop."
  }'
```

## 🚦 Getting Started

1. **Setup Environment**: Configure all API keys and credentials
2. **Share Drive Folder**: Give service account access to your resume folder
3. **Start Server**: `python main.py`
4. **Ingest Resumes**: `POST /api/v1/ingest-resumes`
5. **Start Matching**: `POST /api/v1/match-resumes`

## 🔧 Configuration Options

### Pinecone Settings
- **Index Name**: Customize with `PINECONE_INDEX_NAME`
- **Environment**: Set with `PINECONE_ENVIRONMENT`
- **Dimensions**: Fixed at 1536 for OpenAI embeddings

### Processing Settings
- **Batch Size**: Configurable in `ResumeManager`
- **Top K Results**: Adjustable per request (default: 10)
- **Concurrent Processing**: 5 workers by default

## 🐛 Troubleshooting

### Common Issues

1. **"No PDF files found"**
   - Check Google Drive folder ID
   - Verify service account has access to folder
   - Ensure PDFs are not in subfolders

2. **"Pinecone connection failed"**
   - Verify API key and environment
   - Check if index exists or needs creation

3. **"OpenAI API error"**
   - Verify API key
   - Check rate limits and quota

4. **"Google Drive access denied"**
   - Ensure service account email is shared on folder
   - Check credentials file path

## 📈 Performance Tips

1. **Batch Processing**: Process resumes in batches for better performance
2. **Caching**: Results are cached in Pinecone for fast retrieval
3. **Parallel Processing**: Multiple resumes processed concurrently
4. **Text Optimization**: Resume text is optimized for better embeddings

## 🔒 Security Considerations

- Store credentials securely (never commit to git)
- Use environment variables for sensitive data
- Implement rate limiting for production use
- Consider data privacy regulations for resume data

## 📝 API Documentation

Full interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review API logs for detailed error messages
3. Verify all environment variables are set correctly

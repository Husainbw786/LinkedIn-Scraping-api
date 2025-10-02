import requests
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
import tempfile
import os
from docx import Document
import PyPDF2
from io import BytesIO
from bs4 import BeautifulSoup
from utils.logger_config import setup_logging

logger = setup_logging()

class ResumeExtractionResult:
    """Result of resume text extraction"""
    def __init__(self, text: str, success: bool, error: Optional[str] = None, metadata: Optional[Dict] = None):
        self.text = text
        self.success = success
        self.error = error
        self.metadata = metadata or {}

class ResumeFetcher:
    """Service to fetch and extract text from resume URLs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    async def fetch_resume_text(self, resume_url: str) -> ResumeExtractionResult:
        """
        Fetch and extract text from a resume URL
        
        Supports:
        - Google Docs (public links and export links)
        - PDF files (direct downloads)
        - Word documents (.docx)
        - HTML pages
        - Plain text
        """
        try:
            logger.info(f"Fetching resume from URL: {resume_url}")
            
            # Handle Google Docs URLs
            if self._is_google_docs_url(resume_url):
                return await self._fetch_google_docs(resume_url)
            
            # Handle direct file URLs
            if self._is_direct_file_url(resume_url):
                return await self._fetch_direct_file(resume_url)
            
            # Handle general web pages
            return await self._fetch_web_page(resume_url)
            
        except Exception as e:
            logger.error(f"Error fetching resume from {resume_url}: {str(e)}")
            return ResumeExtractionResult(
                text="",
                success=False,
                error=f"Failed to fetch resume: {str(e)}"
            )
    
    def _is_google_docs_url(self, url: str) -> bool:
        """Check if URL is a Google Docs link"""
        return 'docs.google.com' in url or 'drive.google.com' in url
    
    def _is_direct_file_url(self, url: str) -> bool:
        """Check if URL points to a direct file download"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        return any(path.endswith(ext) for ext in ['.pdf', '.docx', '.doc', '.txt'])
    
    async def _fetch_google_docs(self, url: str) -> ResumeExtractionResult:
        """Fetch content from Google Docs"""
        try:
            # Convert Google Docs URL to export format
            export_url = self._convert_to_export_url(url)
            
            response = self.session.get(export_url, timeout=30)
            
            if response.status_code == 200:
                # Try to extract text from HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Clean up the text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                if len(text.strip()) > 50:  # Minimum content check
                    return ResumeExtractionResult(
                        text=text,
                        success=True,
                        metadata={'source': 'google_docs', 'format': 'html'}
                    )
                else:
                    return ResumeExtractionResult(
                        text="",
                        success=False,
                        error="Document appears to be empty or private. Please ensure the document is publicly accessible."
                    )
            
            elif response.status_code == 403:
                return ResumeExtractionResult(
                    text="",
                    success=False,
                    error="Access denied. Please make sure the Google Doc is publicly accessible or shared with 'Anyone with the link can view'."
                )
            else:
                return ResumeExtractionResult(
                    text="",
                    success=False,
                    error=f"Failed to access Google Doc. Status code: {response.status_code}"
                )
                
        except Exception as e:
            return ResumeExtractionResult(
                text="",
                success=False,
                error=f"Error processing Google Docs URL: {str(e)}"
            )
    
    def _convert_to_export_url(self, url: str) -> str:
        """Convert Google Docs URL to export format"""
        # Extract document ID from various Google Docs URL formats
        doc_id_match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
        if doc_id_match:
            doc_id = doc_id_match.group(1)
            return f"https://docs.google.com/document/d/{doc_id}/export?format=html"
        
        # If already an export URL, return as is
        if 'export?format=' in url:
            return url
        
        # If it's a drive URL, try to convert
        if 'drive.google.com' in url:
            file_id_match = re.search(r'/file/d/([a-zA-Z0-9-_]+)', url)
            if file_id_match:
                file_id = file_id_match.group(1)
                return f"https://drive.google.com/uc?id={file_id}&export=download"
        
        return url
    
    async def _fetch_direct_file(self, url: str) -> ResumeExtractionResult:
        """Fetch and process direct file downloads"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'pdf' in content_type or url.lower().endswith('.pdf'):
                return self._extract_pdf_text(response.content)
            elif 'word' in content_type or url.lower().endswith(('.docx', '.doc')):
                return self._extract_docx_text(response.content)
            elif 'text' in content_type or url.lower().endswith('.txt'):
                return ResumeExtractionResult(
                    text=response.text,
                    success=True,
                    metadata={'source': 'direct_file', 'format': 'text'}
                )
            else:
                # Try to parse as HTML
                return self._extract_html_text(response.content)
                
        except Exception as e:
            return ResumeExtractionResult(
                text="",
                success=False,
                error=f"Error processing direct file: {str(e)}"
            )
    
    async def _fetch_web_page(self, url: str) -> ResumeExtractionResult:
        """Fetch content from a web page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return self._extract_html_text(response.content)
            
        except Exception as e:
            return ResumeExtractionResult(
                text="",
                success=False,
                error=f"Error processing web page: {str(e)}"
            )
    
    def _extract_pdf_text(self, content: bytes) -> ResumeExtractionResult:
        """Extract text from PDF content"""
        try:
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            if text.strip():
                return ResumeExtractionResult(
                    text=text,
                    success=True,
                    metadata={'source': 'direct_file', 'format': 'pdf', 'pages': len(pdf_reader.pages)}
                )
            else:
                return ResumeExtractionResult(
                    text="",
                    success=False,
                    error="Could not extract text from PDF. The file might be image-based or corrupted."
                )
                
        except Exception as e:
            return ResumeExtractionResult(
                text="",
                success=False,
                error=f"Error processing PDF: {str(e)}"
            )
    
    def _extract_docx_text(self, content: bytes) -> ResumeExtractionResult:
        """Extract text from DOCX content"""
        try:
            # Save content to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                
                # Read with python-docx
                doc = Document(tmp_file.name)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                
                # Clean up temporary file
                os.unlink(tmp_file.name)
                
                if text.strip():
                    return ResumeExtractionResult(
                        text=text,
                        success=True,
                        metadata={'source': 'direct_file', 'format': 'docx'}
                    )
                else:
                    return ResumeExtractionResult(
                        text="",
                        success=False,
                        error="Could not extract text from Word document."
                    )
                    
        except Exception as e:
            return ResumeExtractionResult(
                text="",
                success=False,
                error=f"Error processing Word document: {str(e)}"
            )
    
    def _extract_html_text(self, content: bytes) -> ResumeExtractionResult:
        """Extract text from HTML content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            if text.strip():
                return ResumeExtractionResult(
                    text=text,
                    success=True,
                    metadata={'source': 'web_page', 'format': 'html'}
                )
            else:
                return ResumeExtractionResult(
                    text="",
                    success=False,
                    error="Could not extract meaningful text from the webpage."
                )
                
        except Exception as e:
            return ResumeExtractionResult(
                text="",
                success=False,
                error=f"Error processing HTML: {str(e)}"
            )

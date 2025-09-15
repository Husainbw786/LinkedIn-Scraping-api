import PyPDF2
import pdfplumber
import re
from typing import List, Dict, Optional
from fastapi import UploadFile
import io
from loguru import logger
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import string

from models.schemas import ResumeData

class ResumeParser:
    """Parse PDF resumes and extract relevant information"""
    
    def __init__(self):
        self._download_nltk_data()
        self.skills_keywords = self._load_skills_database()
        self.experience_patterns = self._compile_experience_patterns()
    
    def _download_nltk_data(self):
        """Download required NLTK data"""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
    
    def _load_skills_database(self) -> Dict[str, List[str]]:
        """Load comprehensive skills database"""
        return {
            'programming': [
                'python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
                'typescript', 'scala', 'kotlin', 'swift', 'r', 'matlab', 'sql', 'html',
                'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
                'spring', 'laravel', 'rails', '.net', 'asp.net'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
                'oracle', 'sql server', 'sqlite', 'dynamodb', 'firebase'
            ],
            'cloud': [
                'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'terraform',
                'ansible', 'jenkins', 'gitlab ci', 'github actions', 'circleci'
            ],
            'data_science': [
                'machine learning', 'deep learning', 'data analysis', 'pandas', 'numpy',
                'scikit-learn', 'tensorflow', 'pytorch', 'keras', 'tableau', 'power bi',
                'jupyter', 'spark', 'hadoop', 'nlp', 'computer vision'
            ],
            'tools': [
                'git', 'jira', 'confluence', 'slack', 'figma', 'sketch', 'photoshop',
                'illustrator', 'postman', 'swagger', 'linux', 'bash', 'powershell'
            ]
        }
    
    def _compile_experience_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for experience extraction"""
        return {
            'years': re.compile(r'(\d+)[\s\-\+]*(?:years?|yrs?)', re.IGNORECASE),
            'months': re.compile(r'(\d+)[\s\-\+]*(?:months?|mos?)', re.IGNORECASE),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),
            'job_titles': re.compile(r'\b(?:senior|junior|lead|principal|staff|director|manager|engineer|developer|analyst|specialist|consultant|architect|designer|coordinator|supervisor|executive|officer|associate|assistant)\b', re.IGNORECASE)
        }
    
    async def parse_pdf(self, file: UploadFile) -> ResumeData:
        """Parse PDF resume and extract structured data"""
        try:
            # Read file content
            content = await file.read()
            
            # Extract text using both PyPDF2 and pdfplumber for better coverage
            text = self._extract_text_pypdf2(content)
            if not text.strip():
                text = self._extract_text_pdfplumber(content)
            
            if not text.strip():
                raise ValueError("Could not extract text from PDF")
            
            logger.info(f"Extracted {len(text)} characters from resume")
            
            # Parse structured data
            resume_data = self._parse_text_content(text)
            
            return resume_data
            
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise ValueError(f"Failed to parse resume: {str(e)}")
    
    def _extract_text_pypdf2(self, content: bytes) -> str:
        """Extract text using PyPDF2"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {str(e)}")
            return ""
    
    def _extract_text_pdfplumber(self, content: bytes) -> str:
        """Extract text using pdfplumber (better for complex layouts)"""
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {str(e)}")
            return ""
    
    def _parse_text_content(self, text: str) -> ResumeData:
        """Parse extracted text and create structured data"""
        # Clean and normalize text
        clean_text = self._clean_text(text)
        
        # Extract basic information
        name = self._extract_name(clean_text)
        email = self._extract_email(clean_text)
        phone = self._extract_phone(clean_text)
        
        # Extract skills and keywords
        skills = self._extract_skills(clean_text)
        keywords = self._extract_keywords(clean_text)
        
        # Extract experience information
        years_experience = self._extract_years_experience(clean_text)
        experience_level = self._determine_experience_level(years_experience, clean_text)
        
        # Extract job titles and companies
        job_titles = self._extract_job_titles(clean_text)
        companies = self._extract_companies(clean_text)
        
        # Extract education and certifications
        education = self._extract_education(clean_text)
        certifications = self._extract_certifications(clean_text)
        
        return ResumeData(
            name=name,
            email=email,
            phone=phone,
            skills=skills,
            experience_level=experience_level,
            job_titles=job_titles,
            companies=companies,
            education=education,
            certifications=certifications,
            keywords=keywords,
            years_of_experience=years_experience
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract candidate name (simple heuristic)"""
        lines = text.split('\n')[:5]  # Check first 5 lines
        for line in lines:
            line = line.strip()
            # Look for lines with 2-4 words, likely to be names
            words = line.split()
            if 2 <= len(words) <= 4 and all(word.replace('.', '').isalpha() for word in words):
                return line
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address"""
        match = self.experience_patterns['email'].search(text)
        return match.group(0) if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number"""
        match = self.experience_patterns['phone'].search(text)
        return match.group(0) if match else None
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills from text"""
        text_lower = text.lower()
        found_skills = []
        
        # Check all skill categories
        for category, skills_list in self.skills_keywords.items():
            for skill in skills_list:
                if skill.lower() in text_lower:
                    found_skills.append(skill)
        
        # Remove duplicates and return
        return list(set(found_skills))
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords using NLP"""
        try:
            # Tokenize and remove stopwords
            tokens = word_tokenize(text.lower())
            stop_words = set(stopwords.words('english'))
            
            # Filter tokens
            keywords = [
                token for token in tokens 
                if token not in stop_words 
                and token not in string.punctuation 
                and len(token) > 2
                and token.isalpha()
            ]
            
            # Get most frequent keywords
            from collections import Counter
            keyword_counts = Counter(keywords)
            return [word for word, count in keyword_counts.most_common(20)]
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {str(e)}")
            return []
    
    def _extract_years_experience(self, text: str) -> Optional[int]:
        """Extract years of experience"""
        years_matches = self.experience_patterns['years'].findall(text)
        months_matches = self.experience_patterns['months'].findall(text)
        
        total_years = 0
        
        # Sum up years
        for year_str in years_matches:
            try:
                total_years += int(year_str)
            except ValueError:
                continue
        
        # Add months as fractional years
        for month_str in months_matches:
            try:
                total_years += int(month_str) / 12
            except ValueError:
                continue
        
        return int(total_years) if total_years > 0 else None
    
    def _determine_experience_level(self, years: Optional[int], text: str) -> str:
        """Determine experience level based on years and text analysis"""
        text_lower = text.lower()
        
        # Check for explicit level mentions
        if any(word in text_lower for word in ['senior', 'lead', 'principal', 'staff']):
            return 'senior'
        elif any(word in text_lower for word in ['director', 'vp', 'cto', 'ceo', 'executive']):
            return 'executive'
        elif any(word in text_lower for word in ['junior', 'intern', 'entry', 'graduate']):
            return 'entry'
        
        # Determine by years of experience
        if years is None:
            return 'entry'
        elif years < 2:
            return 'entry'
        elif years < 5:
            return 'mid'
        elif years < 10:
            return 'senior'
        else:
            return 'executive'
    
    def _extract_job_titles(self, text: str) -> List[str]:
        """Extract job titles from text"""
        matches = self.experience_patterns['job_titles'].findall(text)
        return list(set(matches))
    
    def _extract_companies(self, text: str) -> List[str]:
        """Extract company names (basic implementation)"""
        # This is a simplified implementation
        # In production, you might use NER or a company database
        lines = text.split('\n')
        companies = []
        
        for line in lines:
            # Look for lines that might contain company names
            if any(word in line.lower() for word in ['inc', 'corp', 'ltd', 'llc', 'company']):
                companies.append(line.strip())
        
        return companies[:5]  # Return top 5
    
    def _extract_education(self, text: str) -> List[str]:
        """Extract education information"""
        education_keywords = [
            'bachelor', 'master', 'phd', 'doctorate', 'mba', 'bs', 'ba', 'ms', 'ma',
            'university', 'college', 'institute', 'school'
        ]
        
        text_lower = text.lower()
        education = []
        
        for keyword in education_keywords:
            if keyword in text_lower:
                # Find the line containing the education keyword
                lines = text.split('\n')
                for line in lines:
                    if keyword in line.lower():
                        education.append(line.strip())
                        break
        
        return list(set(education))[:3]  # Return top 3
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications"""
        cert_keywords = [
            'certified', 'certification', 'certificate', 'aws', 'azure', 'gcp',
            'pmp', 'cissp', 'cisa', 'cism', 'comptia', 'cisco', 'microsoft'
        ]
        
        text_lower = text.lower()
        certifications = []
        
        for keyword in cert_keywords:
            if keyword in text_lower:
                lines = text.split('\n')
                for line in lines:
                    if keyword in line.lower():
                        certifications.append(line.strip())
                        break
        
        return list(set(certifications))[:5]  # Return top 5

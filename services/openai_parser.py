from openai import OpenAI
import json
import logging
import os
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

from models.schemas import JobDescription

# Load environment variables from .env file
load_dotenv()

# Setup logger
logger = logging.getLogger(__name__)

class OpenAIJobParser:
    """Parse job descriptions using OpenAI to extract structured data"""
    
    def __init__(self):
        # Get API key from environment
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found. Using fallback parsing.")
            self.use_openai = False
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                self.use_openai = True
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.use_openai = False
                self.client = None
        
        # Fallback skill extraction patterns
        self.common_skills = [
            "Python", "JavaScript", "Java", "C++", "C#", "Go", "Rust", "TypeScript", "PHP", "Ruby",
            "React", "Angular", "Vue.js", "Node.js", "Express", "Django", "Flask", "Spring", "Laravel",
            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "Git", "CI/CD", "DevOps",
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
            "Machine Learning", "Data Science", "AI", "Deep Learning", "TensorFlow", "PyTorch",
            "Pandas", "NumPy", "Scikit-learn", "Apache Spark", "Hadoop", "Kafka",
            "REST API", "GraphQL", "Microservices", "Agile", "Scrum", "Jira", "Confluence",
            "Linux", "Unix", "Terraform", "Ansible", "Prometheus", "Grafana", "ELK Stack"
        ]
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def parse_job_description(self, job_text: str, company: Optional[str] = None) -> JobDescription:
        """
        Parse a job description text and extract structured information
        """
        try:
            if self.use_openai:
                return await self._parse_with_openai(job_text, company)
            else:
                return self._parse_with_fallback(job_text, company)
                
        except Exception as e:
            logger.error(f"Job description parsing failed: {str(e)}")
            return self._parse_with_fallback(job_text, company)
    
    async def _parse_with_openai(self, job_text: str, company: Optional[str] = None) -> JobDescription:
        """Parse job description using OpenAI"""
        
        system_prompt = """You are an expert HR assistant that extracts structured information from job descriptions. 
        
        Extract the following information from the job description and return it as a JSON object:
        - title: The job title
        - company: Company name (if not provided separately)
        - required_skills: List of must-have technical skills
        - preferred_skills: List of nice-to-have skills
        - experience_level: One of "entry", "mid", "senior", "executive"
        - location: Job location (extract from text or use "Remote" if remote work mentioned)
        - employment_type: "Full-time", "Part-time", "Contract", etc.
        - salary_range: Salary range if mentioned
        
        Be specific about technical skills and avoid generic terms. Focus on programming languages, frameworks, tools, and technologies."""
        
        user_prompt = f"""Job Description:
        {job_text}
        
        Company: {company or "Not specified"}
        
        Please extract the structured information as JSON."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # Extract JSON from response
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON if it's wrapped in markdown
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            
            parsed_data = json.loads(content)
            
            # Create JobDescription object
            return JobDescription(
                title=parsed_data.get("title", "Unknown Position"),
                company=company or parsed_data.get("company", "Unknown Company"),
                description=job_text,
                required_skills=parsed_data.get("required_skills", []),
                preferred_skills=parsed_data.get("preferred_skills", []),
                experience_level=parsed_data.get("experience_level", "mid"),
                location=parsed_data.get("location", "Not specified"),
                employment_type=parsed_data.get("employment_type", "Full-time"),
                salary_range=parsed_data.get("salary_range")
            )
            
        except Exception as e:
            logger.error(f"OpenAI parsing failed: {str(e)}")
            return self._parse_with_fallback(job_text, company)
    
    def _parse_with_fallback(self, job_text: str, company: Optional[str] = None) -> JobDescription:
        """Fallback parsing using pattern matching"""
        
        job_text_lower = job_text.lower()
        
        # Extract title (look for common patterns)
        title = self._extract_title(job_text)
        
        # Extract skills
        required_skills = []
        preferred_skills = []
        
        for skill in self.common_skills:
            if skill.lower() in job_text_lower:
                # Determine if it's required or preferred based on context
                skill_context = self._get_skill_context(job_text_lower, skill.lower())
                if any(word in skill_context for word in ["required", "must", "essential", "mandatory"]):
                    required_skills.append(skill)
                else:
                    preferred_skills.append(skill)
        
        # If no required skills found, move some preferred to required
        if not required_skills and preferred_skills:
            required_skills = preferred_skills[:3]
            preferred_skills = preferred_skills[3:]
        
        # Extract experience level
        experience_level = self._extract_experience_level(job_text_lower)
        
        # Extract location
        location = self._extract_location(job_text)
        
        # Extract employment type
        employment_type = self._extract_employment_type(job_text_lower)
        
        # Extract salary range
        salary_range = self._extract_salary_range(job_text)
        
        return JobDescription(
            title=title,
            company=company or "Unknown Company",
            description=job_text,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            experience_level=experience_level,
            location=location,
            employment_type=employment_type,
            salary_range=salary_range
        )
    
    def _extract_title(self, job_text: str) -> str:
        """Extract job title from text"""
        lines = job_text.split('\n')
        first_line = lines[0].strip()
        
        # Common job title patterns
        job_titles = [
            "engineer", "developer", "manager", "analyst", "scientist", "architect",
            "designer", "consultant", "specialist", "coordinator", "director", "lead"
        ]
        
        if any(title in first_line.lower() for title in job_titles):
            return first_line
        
        # Look for title in the text
        for line in lines[:5]:  # Check first 5 lines
            if any(title in line.lower() for title in job_titles):
                return line.strip()
        
        return "Software Engineer"  # Default
    
    def _get_skill_context(self, text: str, skill: str) -> str:
        """Get context around a skill mention"""
        skill_index = text.find(skill)
        if skill_index == -1:
            return ""
        
        start = max(0, skill_index - 50)
        end = min(len(text), skill_index + len(skill) + 50)
        return text[start:end]
    
    def _extract_experience_level(self, job_text: str) -> str:
        """Extract experience level from job text"""
        if any(word in job_text for word in ["senior", "lead", "principal", "staff", "architect"]):
            return "senior"
        elif any(word in job_text for word in ["junior", "entry", "graduate", "intern", "associate"]):
            return "entry"
        elif any(word in job_text for word in ["director", "vp", "head", "chief", "executive"]):
            return "executive"
        else:
            return "mid"
    
    def _extract_location(self, job_text: str) -> str:
        """Extract location from job text"""
        if any(word in job_text.lower() for word in ["remote", "work from home", "wfh"]):
            return "Remote"
        
        # Look for common location patterns
        import re
        location_pattern = r'([A-Z][a-z]+,\s*[A-Z]{2})|([A-Z][a-z]+\s+[A-Z][a-z]+,\s*[A-Z]{2})'
        matches = re.findall(location_pattern, job_text)
        
        if matches:
            return matches[0][0] or matches[0][1]
        
        return "Not specified"
    
    def _extract_employment_type(self, job_text: str) -> str:
        """Extract employment type from job text"""
        if "part-time" in job_text or "part time" in job_text:
            return "Part-time"
        elif "contract" in job_text or "contractor" in job_text:
            return "Contract"
        elif "freelance" in job_text:
            return "Freelance"
        elif "intern" in job_text:
            return "Internship"
        else:
            return "Full-time"
    
    def _extract_salary_range(self, job_text: str) -> Optional[str]:
        """Extract salary range from job text"""
        import re
        
        # Look for salary patterns
        salary_patterns = [
            r'\$[\d,]+\s*-\s*\$[\d,]+',
            r'\$[\d,]+k?\s*-\s*\$?[\d,]+k?',
            r'[\d,]+k?\s*-\s*[\d,]+k?\s*(?:USD|dollars?)',
        ]
        
        for pattern in salary_patterns:
            matches = re.findall(pattern, job_text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None

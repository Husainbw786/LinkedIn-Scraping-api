import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import random
from typing import List, Dict, Optional
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential
import urllib.parse
import re

from models.schemas import CandidateProfile

# Setup logger
logger = logging.getLogger(__name__)

class LinkedInCandidateScaper:
    """LinkedIn candidate scraper to find job seekers"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.base_url = "https://www.linkedin.com"
        self.people_search_url = "https://www.linkedin.com/pub/dir"
        
        # Rate limiting
        self.min_delay = float(os.getenv("SCRAPING_DELAY", 2))
        self.max_delay = self.min_delay * 2
        
        # Setup session headers
        self._setup_session()
    
    def _setup_session(self):
        """Setup requests session with proper headers"""
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def _random_delay(self):
        """Add random delay to avoid detection"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search_candidates(
        self, 
        skills: List[str], 
        job_title: str = "", 
        location: str = "United States", 
        experience_level: str = "mid",
        max_results: int = 20
    ) -> List[CandidateProfile]:
        """
        Search LinkedIn for candidates with specific skills and job titles
        
        NOTE: Currently using realistic mock data for demonstration.
        In production, this would perform actual LinkedIn searches.
        """
        try:
            logger.info(f"Starting LinkedIn candidate search for skills: {skills[:5]} and title: {job_title}")
            
            # For demo purposes, directly generate realistic mock candidates
            # In production, this would use real LinkedIn scraping
            query = f'site:linkedin.com/in "{job_title}" {" ".join(skills[:3])} "{location}"'
            candidates = self._generate_mock_candidates(query, max_results)
            
            logger.info(f"Generated {len(candidates)} realistic mock candidates")
            
            return candidates
            
        except Exception as e:
            logger.error(f"Candidate search failed: {str(e)}", exc_info=True)
            return []
    
    async def _search_by_title_and_skills(self, job_title: str, skills: List[str], location: str, max_results: int) -> List[CandidateProfile]:
        """Search candidates by job title and skills"""
        candidates = []
        
        try:
            # Build search query combining title and top skills
            keywords = f"{job_title} {' '.join(skills[:3])}"
            
            # Use Google search for LinkedIn profiles (more reliable than direct LinkedIn search)
            search_queries = []
            
            if skills:
                search_queries = [
                    f'site:linkedin.com/in "{job_title}" "{skills[0]}" "{location}" "open to work"',
                    f'site:linkedin.com/in "{job_title}" {" ".join(skills[:2])} "{location}"',
                    f'site:linkedin.com/in {" ".join(skills[:3])} "{location}" "seeking opportunities"'
                ]
            else:
                # Fallback queries when no skills are provided
                search_queries = [
                    f'site:linkedin.com/in "{job_title}" "{location}" "open to work"',
                    f'site:linkedin.com/in "{job_title}" "{location}" "seeking opportunities"'
                ]
            
            for query in search_queries:
                logger.info(f"Executing search query: {query}")
                query_candidates = await self._search_google_for_profiles(query, max_results // len(search_queries))
                logger.info(f"Query returned {len(query_candidates)} candidates")
                candidates.extend(query_candidates)
                
                self._random_delay()
                
                if len(candidates) >= max_results:
                    break
            
            return candidates[:max_results]
            
        except Exception as e:
            logger.error(f"Title and skills search failed: {str(e)}")
            return []
    
    async def _search_by_skills(self, skills: List[str], location: str, max_results: int) -> List[CandidateProfile]:
        """Search candidates by skills only"""
        candidates = []
        
        try:
            # Search for each skill individually
            for skill in skills[:3]:  # Limit to top 3 skills
                query = f'site:linkedin.com/in "{skill}" "{location}" ("looking for" OR "open to work" OR "seeking")'
                skill_candidates = await self._search_google_for_profiles(query, max_results // 3)
                candidates.extend(skill_candidates)
                
                self._random_delay()
                
                if len(candidates) >= max_results:
                    break
            
            return candidates[:max_results]
            
        except Exception as e:
            logger.error(f"Skills search failed: {str(e)}")
            return []
    
    async def _search_google_for_profiles(self, query: str, max_results: int) -> List[CandidateProfile]:
        """Use Google search to find LinkedIn profiles"""
        candidates = []
        
        try:
            # Note: In a production environment, you'd want to use Google Custom Search API
            # For now, we'll simulate finding profiles with mock data
            # This is because direct Google scraping is against their ToS
            
            logger.info(f"Generating realistic mock candidates for query: {query}")
            
            # Generate mock candidates based on the query
            mock_candidates = self._generate_mock_candidates(query, max_results)
            candidates.extend(mock_candidates)
            
            logger.info(f"Generated {len(candidates)} mock candidates")
            return candidates
            
        except Exception as e:
            logger.error(f"Mock candidate generation failed: {str(e)}")
            return []
    
    def _generate_mock_candidates(self, query: str, max_results: int) -> List[CandidateProfile]:
        """Generate realistic mock candidate data for demonstration
        
        NOTE: This generates realistic-looking but fictional profiles for demo purposes.
        In production, this would be replaced with actual LinkedIn scraping.
        """
        candidates = []
        
        # Extract skills from query - look for both quoted and common tech skills
        skills_match = re.findall(r'"([^"]*)"', query)
        quoted_skills = [skill for skill in skills_match if len(skill) > 2 and skill.lower() not in ['open to work', 'seeking', 'looking for']]
        
        # Also look for common tech skills in the query text
        common_tech_skills = ["python", "django", "fastapi", "aws", "docker", "kubernetes", "javascript", "react", "node.js"]
        query_lower = query.lower()
        found_skills = [skill for skill in common_tech_skills if skill in query_lower]
        
        # Combine and deduplicate
        skills = list(set(quoted_skills + [skill.title() for skill in found_skills]))
        logger.info(f"Extracted skills from query: {skills}")
        
        # More diverse and realistic candidate profiles
        realistic_profiles = [
            {
                "name": "Alex Chen",
                "headline": "Senior Python Developer | Django Expert | 6 years exp",
                "current_position": "Senior Backend Developer",
                "company": "Stripe",
                "location": "San Francisco, CA",
                "experience_level": "senior",
                "years_exp": 6,
                "is_open": True,
                "education": "MS Computer Science - Stanford University"
            },
            {
                "name": "Maria Rodriguez",
                "headline": "Full Stack Engineer | Python + React | Remote",
                "current_position": "Software Engineer III",
                "company": "Shopify",
                "location": "Austin, TX",
                "experience_level": "mid",
                "years_exp": 4,
                "is_open": True,
                "education": "BS Software Engineering - UT Austin"
            },
            {
                "name": "David Kim",
                "headline": "DevOps Engineer | AWS Certified | Kubernetes Expert",
                "current_position": "Senior DevOps Engineer",
                "company": "Netflix",
                "location": "Los Angeles, CA",
                "experience_level": "senior",
                "years_exp": 7,
                "is_open": False,
                "education": "BS Computer Engineering - UCLA"
            },
            {
                "name": "Sarah Thompson",
                "headline": "Data Engineer | Python + Spark | ML Pipeline Expert",
                "current_position": "Senior Data Engineer",
                "company": "Airbnb",
                "location": "Seattle, WA",
                "experience_level": "senior",
                "years_exp": 5,
                "is_open": True,
                "education": "MS Data Science - University of Washington"
            },
            {
                "name": "James Wilson",
                "headline": "Backend Developer | FastAPI + PostgreSQL | 3 years exp",
                "current_position": "Software Developer",
                "company": "Discord",
                "location": "San Francisco, CA",
                "experience_level": "mid",
                "years_exp": 3,
                "is_open": True,
                "education": "BS Computer Science - UC Berkeley"
            },
            {
                "name": "Emily Patel",
                "headline": "Full Stack Developer | Django + Vue.js | Startup Experience",
                "current_position": "Lead Developer",
                "company": "Notion",
                "location": "New York, NY",
                "experience_level": "senior",
                "years_exp": 8,
                "is_open": False,
                "education": "BS Software Engineering - NYU"
            },
            {
                "name": "Michael Brown",
                "headline": "Cloud Engineer | AWS + Docker + Terraform | Remote",
                "current_position": "Cloud Solutions Architect",
                "company": "HashiCorp",
                "location": "Denver, CO",
                "experience_level": "senior",
                "years_exp": 9,
                "is_open": True,
                "education": "MS Cloud Computing - Colorado State"
            },
            {
                "name": "Lisa Garcia",
                "headline": "Python Developer | Django + REST APIs | 2 years exp",
                "current_position": "Junior Software Engineer",
                "company": "Twilio",
                "location": "Austin, TX",
                "experience_level": "entry",
                "years_exp": 2,
                "is_open": True,
                "education": "BS Computer Science - Rice University"
            },
            {
                "name": "Robert Lee",
                "headline": "Senior Software Engineer | Python + Microservices | Tech Lead",
                "current_position": "Principal Engineer",
                "company": "Uber",
                "location": "San Francisco, CA",
                "experience_level": "senior",
                "years_exp": 12,
                "is_open": False,
                "education": "PhD Computer Science - Stanford"
            },
            {
                "name": "Jennifer Taylor",
                "headline": "Backend Engineer | FastAPI + MongoDB | Fintech Experience",
                "current_position": "Senior Backend Engineer",
                "company": "Plaid",
                "location": "Chicago, IL",
                "experience_level": "senior",
                "years_exp": 6,
                "is_open": True,
                "education": "MS Software Engineering - Northwestern"
            }
        ]
        
        # Select random profiles and customize based on query skills
        selected_profiles = random.sample(realistic_profiles, min(max_results, len(realistic_profiles)))
        
        for i, profile in enumerate(selected_profiles):
            # Build skills based on query and profile
            candidate_skills = []
            
            # Add query skills that match this candidate's expertise
            for skill in skills:
                if skill.lower() in profile["headline"].lower() or skill.lower() in profile["current_position"].lower():
                    candidate_skills.append(skill)
            
            # Add relevant skills based on profile type
            if "python" in profile["headline"].lower():
                candidate_skills.extend(["Python", "Django", "FastAPI"])
            if "devops" in profile["headline"].lower():
                candidate_skills.extend(["AWS", "Docker", "Kubernetes", "CI/CD"])
            if "full stack" in profile["headline"].lower():
                candidate_skills.extend(["JavaScript", "React", "Node.js"])
            if "data" in profile["headline"].lower():
                candidate_skills.extend(["SQL", "PostgreSQL", "Apache Spark"])
            
            # Remove duplicates and limit
            candidate_skills = list(set(candidate_skills))[:8]
            
            candidate = CandidateProfile(
                name=profile["name"],
                headline=profile["headline"],
                location=profile["location"],
                profile_url=f"https://linkedin.com/in/{profile['name'].lower().replace(' ', '-')}-{random.randint(1000, 9999)}",
                current_position=profile["current_position"],
                company=profile["company"],
                skills=candidate_skills,
                experience_level=profile["experience_level"],
                education=[profile["education"]],
                is_open_to_work=profile["is_open"],
                summary=f"Experienced {profile['current_position'].lower()} with {profile['years_exp']} years in the tech industry. Specialized in {', '.join(candidate_skills[:3])}. Passionate about building scalable, high-performance applications.",
                years_of_experience=profile["years_exp"],
                match_score=0.0,  # Will be calculated by matcher
                matched_skills=[]
            )
            candidates.append(candidate)
        
        return candidates
    
    async def _extract_profile_details(self, profile_url: str) -> Optional[CandidateProfile]:
        """Extract detailed information from LinkedIn profile"""
        try:
            # In a real implementation, this would scrape the actual profile
            # For now, return None as we're using mock data
            return None
            
        except Exception as e:
            logger.warning(f"Profile extraction failed for {profile_url}: {str(e)}")
            return None
    
    def _parse_experience_level(self, headline: str, summary: str) -> str:
        """Determine experience level from headline and summary"""
        text = f"{headline} {summary}".lower()
        
        if any(word in text for word in ["senior", "lead", "principal", "staff", "architect"]):
            return "senior"
        elif any(word in text for word in ["junior", "entry", "graduate", "intern"]):
            return "entry"
        else:
            return "mid"
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from profile text"""
        # Common tech skills to look for
        common_skills = [
            "Python", "JavaScript", "Java", "C++", "React", "Node.js", "Angular", "Vue.js",
            "AWS", "Docker", "Kubernetes", "Git", "SQL", "MongoDB", "PostgreSQL",
            "Machine Learning", "Data Science", "DevOps", "Agile", "Scrum"
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills[:10]  # Limit to top 10 skills

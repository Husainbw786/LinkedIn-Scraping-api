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

from models.schemas import JobResult

# Setup logger
logger = logging.getLogger(__name__)

class LinkedInScraper:
    """LinkedIn job scraper with anti-detection measures"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.driver = None
        self.base_url = "https://www.linkedin.com"
        self.jobs_url = "https://www.linkedin.com/jobs/search"
        
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
    
    def _setup_driver(self):
        """Selenium not available in serverless environment"""
        raise NotImplementedError("Selenium not supported in serverless deployment")
    
    def _random_delay(self):
        """Add random delay to avoid detection"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search_jobs(
        self, 
        skills: List[str], 
        experience_level: str = "entry",
        location: str = "United States",
        max_results: int = 20
    ) -> List[JobResult]:
        """
        Search LinkedIn jobs using multiple strategies
        """
        try:
            logger.info(f"Starting LinkedIn job search for skills: {skills[:5]}")
            
            # Use only requests-based scraping for serverless deployment
            jobs = await self._search_with_requests(skills, location, max_results)
            
            # Remove duplicates based on job URL
            unique_jobs = {}
            for job in jobs:
                if job.job_url not in unique_jobs:
                    unique_jobs[job.job_url] = job
            
            result = list(unique_jobs.values())[:max_results]
            logger.info(f"Found {len(result)} unique jobs")
            
            return result
            
        except Exception as e:
            logger.error(f"Job search failed: {str(e)}")
            return []
    
    async def _search_with_requests(self, skills: List[str], location: str, max_results: int) -> List[JobResult]:
        """Search jobs using requests (public LinkedIn job search)"""
        jobs = []
        
        try:
            # Build search query
            keywords = " OR ".join(skills[:5])  # Use top 5 skills
            
            params = {
                'keywords': keywords,
                'location': location,
                'f_TPR': 'r2592000',  # Past month
                'f_JT': 'F',  # Full-time
                'start': 0
            }
            
            # Search multiple pages
            for page in range(0, min(max_results // 10, 5)):  # Max 5 pages
                params['start'] = page * 25
                
                url = f"{self.jobs_url}?" + urllib.parse.urlencode(params)
                logger.info(f"Scraping page {page + 1}: {url}")
                
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                page_jobs = self._parse_job_listings(response.text, url)
                jobs.extend(page_jobs)
                
                self._random_delay()
                
                if len(jobs) >= max_results:
                    break
            
            return jobs[:max_results]
            
        except Exception as e:
            logger.error(f"Requests-based search failed: {str(e)}")
            return []
    
    async def _search_with_selenium(self, skills: List[str], experience_level: str, location: str, max_results: int) -> List[JobResult]:
        """Selenium not available in serverless environment"""
        logger.warning("Selenium scraping not available in serverless deployment")
        return []
    
    def _parse_job_listings(self, html: str, source_url: str) -> List[JobResult]:
        """Parse job listings from HTML"""
        jobs = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find job cards (LinkedIn's structure may change)
            job_cards = soup.find_all('div', {'class': lambda x: x and 'job-search-card' in x}) or \
                       soup.find_all('li', {'class': lambda x: x and 'result-card' in x}) or \
                       soup.find_all('div', {'data-job-id': True})
            
            for card in job_cards:
                try:
                    job = self._extract_job_from_soup(card, source_url)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse job card: {str(e)}")
                    continue
            
            return jobs
            
        except Exception as e:
            logger.error(f"HTML parsing failed: {str(e)}")
            return []
    
    def _extract_job_from_soup(self, card, source_url: str) -> Optional[JobResult]:
        """Extract job information from BeautifulSoup element"""
        try:
            # Extract title
            title_elem = card.find('h3') or card.find('a', {'class': lambda x: x and 'job-title' in str(x).lower()})
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
            
            # Extract company
            company_elem = card.find('h4') or card.find('a', {'class': lambda x: x and 'company' in str(x).lower()})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
            
            # Extract location
            location_elem = card.find('div', {'class': lambda x: x and 'location' in str(x).lower()})
            location = location_elem.get_text(strip=True) if location_elem else "Unknown Location"
            
            # Extract job URL
            link_elem = card.find('a', href=True)
            job_url = link_elem['href'] if link_elem else source_url
            if job_url.startswith('/'):
                job_url = self.base_url + job_url
            
            # Extract description (limited in search results)
            desc_elem = card.find('p') or card.find('div', {'class': lambda x: x and 'summary' in str(x).lower()})
            description = desc_elem.get_text(strip=True) if desc_elem else "No description available"
            
            return JobResult(
                title=title,
                company=company,
                location=location,
                description=description[:500],  # Limit description length
                job_url=job_url,
                employment_type="Full-time",  # Default
                required_skills=[],  # Will be populated by job matcher
                match_score=0.0
            )
            
        except Exception as e:
            logger.warning(f"Job extraction failed: {str(e)}")
            return None
    
    def _extract_job_from_card(self, card):
        """Selenium not available in serverless environment"""
        return None
    
    def _scroll_to_load_jobs(self):
        """Selenium not available in serverless environment"""
        pass
    
    def __del__(self):
        """Cleanup - no driver in serverless mode"""
        pass

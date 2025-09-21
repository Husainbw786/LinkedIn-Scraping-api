import requests
import os
from typing import List, Dict, Any, Optional
from utils.logger_config import setup_logging

logger = setup_logging()

class CrustDataAPI:
    """Service to interact with CrustData API for candidate search"""
    
    def __init__(self):
        self.base_url = "https://api.crustdata.com/screener/person/search"
        self.api_token = os.getenv("CRUSTDATA_API_TOKEN")
        if not self.api_token:
            raise ValueError("CRUSTDATA_API_TOKEN environment variable is required")
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def search_candidates(
        self,
        job_titles: List[str],
        functions: List[str],
        keywords: List[str],
        locations: List[str],
        experience_levels: List[str],
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search for candidates using CrustData API
        
        Args:
            job_titles: List of job titles to search for
            functions: List of functions/departments (e.g., "Engineering", "Information Technology")
            keywords: List of keywords/skills to search for
            locations: List of locations to search in
            experience_levels: List of experience levels (e.g., "6 to 10 years", "More than 10 years")
            page: Page number for pagination
            
        Returns:
            Dict containing the API response with candidate profiles
        """
        try:
            # Build filters for the API request
            filters = []
            
            if job_titles:
                filters.append({
                    "filter_type": "CURRENT_TITLE",
                    "type": "in",
                    "value": job_titles
                })
            
            if functions:
                filters.append({
                    "filter_type": "FUNCTION",
                    "type": "in", 
                    "value": functions
                })
            
            if keywords:
                # Join keywords with spaces for better search
                keyword_string = " ".join(keywords)
                filters.append({
                    "filter_type": "KEYWORD",
                    "type": "in",
                    "value": [keyword_string]
                })
            
            if locations:
                filters.append({
                    "filter_type": "REGION",
                    "type": "in",
                    "value": locations
                })
            
            if experience_levels:
                filters.append({
                    "filter_type": "YEARS_OF_EXPERIENCE",
                    "type": "in",
                    "value": experience_levels
                })
            
            payload = {
                "filters": filters,
                "page": page
            }
            
            logger.info(f"Searching candidates with filters: {filters}")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60  # Increased timeout to 60 seconds
            )
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Found {len(data.get('profiles', []))} candidates")
            
            return data
            
        except requests.exceptions.Timeout as e:
            logger.error(f"CrustData API timeout: {str(e)}")
            # Return empty result instead of failing completely
            return {"profiles": [], "message": "API timeout - please try again"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling CrustData API: {str(e)}")
            # Return empty result for network issues
            return {"profiles": [], "message": f"API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error in candidate search: {str(e)}")
            return {"profiles": [], "message": f"Search failed: {str(e)}"}
    
    def format_candidate_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw CrustData profile data into our standard format
        
        Args:
            profile_data: Raw profile data from CrustData API
            
        Returns:
            Formatted candidate profile
        """
        try:
            # Extract years of experience from employer history
            years_exp = self._calculate_experience(profile_data.get('employer', []))
            
            formatted_profile = {
                "name": profile_data.get("name", ""),
                "location": profile_data.get("location", ""),
                "linkedin_profile_url": profile_data.get("linkedin_profile_url", ""),
                "linkedin_profile_urn": profile_data.get("linkedin_profile_urn", ""),
                "default_position_title": profile_data.get("default_position_title", ""),
                "headline": profile_data.get("headline", ""),
                "summary": profile_data.get("summary", ""),
                "num_of_connections": profile_data.get("num_of_connections", 0),
                "skills": profile_data.get("skills", []),
                "current_title": profile_data.get("current_title", ""),
                "profile_picture_url": profile_data.get("profile_picture_url", ""),
                "employer": profile_data.get("employer", []),
                "education_background": profile_data.get("education_background", []),
                "emails": profile_data.get("emails", []),
                "websites": profile_data.get("websites", []),
                "years_of_experience": years_exp,
                "match_score": 0.0,  # Will be calculated by matcher
                "match_explanation": None
            }
            
            return formatted_profile
            
        except Exception as e:
            logger.error(f"Error formatting candidate profile: {str(e)}")
            return {}
    
    def _calculate_experience(self, employer_history: List[Dict[str, Any]]) -> Optional[str]:
        """
        Calculate years of experience from employer history
        
        Args:
            employer_history: List of employment records
            
        Returns:
            String representation of years of experience
        """
        try:
            if not employer_history:
                return None
            
            from datetime import datetime
            
            total_months = 0
            
            for job in employer_history:
                start_date = job.get("start_date")
                end_date = job.get("end_date")
                
                if start_date:
                    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    end = datetime.now()
                    
                    if end_date:
                        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    
                    months = (end.year - start.year) * 12 + (end.month - start.month)
                    total_months += max(0, months)
            
            years = total_months // 12
            
            if years < 2:
                return "0 to 2 years"
            elif years < 6:
                return "2 to 6 years"
            elif years < 10:
                return "6 to 10 years"
            else:
                return "More than 10 years"
                
        except Exception as e:
            logger.error(f"Error calculating experience: {str(e)}")
            return None

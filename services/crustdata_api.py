import requests
import os
from typing import List, Dict, Any, Optional
from utils.logger_config import setup_logging
from .openai_job_parser import OpenAIJobParser

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
        self.openai_parser = OpenAIJobParser()
    
    async def search_candidates_from_job_description(self, job_description: str, page: int = 1) -> Dict[str, Any]:
        """
        Search for candidates using OpenAI to parse job description and generate optimal filters
        
        Args:
            job_description: Raw job description text
            page: Page number for pagination
            
        Returns:
            Dict containing the API response with candidate profiles and parsing info
        """
        try:
            logger.info("Starting intelligent candidate search with OpenAI parsing")
            
            # Use OpenAI to parse job description and generate optimal filters
            parsed_filters = self.openai_parser.parse_job_description(job_description)
            
            logger.info(f"OpenAI generated filters: {parsed_filters}")
            
            # Build CrustData API filters from OpenAI output
            filters = []
            
            if parsed_filters.get("job_titles"):
                filters.append({
                    "filter_type": "CURRENT_TITLE",
                    "type": "in",
                    "value": parsed_filters["job_titles"]
                })
            
            if parsed_filters.get("functions"):
                filters.append({
                    "filter_type": "FUNCTION",
                    "type": "in",
                    "value": parsed_filters["functions"]
                })
            
            if parsed_filters.get("keywords"):
                # Join keywords for search
                keyword_string = " ".join(parsed_filters["keywords"])
                filters.append({
                    "filter_type": "KEYWORD",
                    "type": "in",
                    "value": [keyword_string]
                })
            
            if parsed_filters.get("locations"):
                filters.append({
                    "filter_type": "REGION",
                    "type": "in",
                    "value": parsed_filters["locations"]
                })
            
            if parsed_filters.get("experience_levels"):
                filters.append({
                    "filter_type": "YEARS_OF_EXPERIENCE",
                    "type": "in",
                    "value": parsed_filters["experience_levels"]
                })
            
            # Make the API call
            payload = {
                "filters": filters,
                "page": page
            }
            
            logger.info(f"Calling CrustData API with filters: {filters}")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            data = response.json()
            
            profiles_found = len(data.get('profiles', []))
            logger.info(f"Found {profiles_found} candidates")
            
            # If no results and we have multiple filters, try simplified search
            if profiles_found == 0 and len(filters) > 2:
                logger.info("No results with full filters, trying simplified search...")
                return await self._simplified_search(parsed_filters, page)
            
            # Add parsing info to response
            data['parsing_info'] = {
                'filters_used': parsed_filters,
                'search_strategy': parsed_filters.get('search_strategy', 'OpenAI optimized search'),
                'total_filters_applied': len(filters)
            }
            
            return data
            
        except requests.exceptions.Timeout as e:
            logger.error(f"CrustData API timeout: {str(e)}")
            return {"profiles": [], "message": "API timeout - please try again", "parsing_info": {}}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling CrustData API: {str(e)}")
            return {"profiles": [], "message": f"API error: {str(e)}", "parsing_info": {}}
        except Exception as e:
            logger.error(f"Unexpected error in candidate search: {str(e)}")
            return {"profiles": [], "message": f"Search failed: {str(e)}", "parsing_info": {}}
    
    async def _simplified_search(self, parsed_filters: Dict[str, Any], page: int = 1) -> Dict[str, Any]:
        """
        Simplified search with only the most important filters
        """
        try:
            logger.info("Performing simplified search")
            
            # Use only job titles and top keyword
            filters = []
            
            if parsed_filters.get("job_titles"):
                filters.append({
                    "filter_type": "CURRENT_TITLE",
                    "type": "in",
                    "value": parsed_filters["job_titles"][:2]  # Only top 2 job titles
                })
            
            if parsed_filters.get("keywords"):
                # Use only the most important keyword
                top_keyword = parsed_filters["keywords"][0] if parsed_filters["keywords"] else "Software"
                filters.append({
                    "filter_type": "KEYWORD",
                    "type": "in",
                    "value": [top_keyword]
                })
            
            payload = {
                "filters": filters,
                "page": page
            }
            
            logger.info(f"Simplified search with filters: {filters}")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            data = response.json()
            
            profiles_found = len(data.get('profiles', []))
            logger.info(f"Simplified search found {profiles_found} candidates")
            
            # Add parsing info
            data['parsing_info'] = {
                'filters_used': parsed_filters,
                'search_strategy': 'Simplified search - reduced filters for broader results',
                'total_filters_applied': len(filters),
                'note': 'Used simplified search due to no results with full filters'
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Simplified search failed: {str(e)}")
            return {
                "profiles": [], 
                "message": f"Both full and simplified searches failed: {str(e)}",
                "parsing_info": {}
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
            # Build filters for the API request - make it more flexible
            filters = []
            
            # Start with broader job titles if specific ones don't work
            if job_titles:
                # Add both specific and broader titles
                broad_titles = ["Software Engineer", "Backend Engineer", "Python Developer", "Software Developer"]
                all_titles = list(set(job_titles + broad_titles))
                filters.append({
                    "filter_type": "CURRENT_TITLE",
                    "type": "in",
                    "value": all_titles
                })
            
            if functions:
                filters.append({
                    "filter_type": "FUNCTION",
                    "type": "in", 
                    "value": functions
                })
            
            # Use only the most important keywords to avoid being too restrictive
            if keywords:
                # Take only top 3-5 most important keywords
                important_keywords = keywords[:5]
                keyword_string = " ".join(important_keywords)
                filters.append({
                    "filter_type": "KEYWORD",
                    "type": "in",
                    "value": [keyword_string]
                })
            
            # Try broader location search
            if locations:
                # If US is specified, try different formats
                broad_locations = []
                for loc in locations:
                    if "united states" in loc.lower() or "usa" in loc.lower():
                        broad_locations.extend([
                            "United States",
                            "USA", 
                            "California, United States",
                            "New York, United States",
                            "Texas, United States"
                        ])
                    else:
                        broad_locations.append(loc)
                
                filters.append({
                    "filter_type": "REGION",
                    "type": "in",
                    "value": list(set(broad_locations))
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
            profiles_found = len(data.get('profiles', []))
            logger.info(f"Found {profiles_found} candidates")
            
            # If no results found, try a simpler search
            if profiles_found == 0 and len(filters) > 2:
                logger.info("No candidates found with full filters, trying simplified search...")
                return await self._fallback_search(job_titles, keywords, page)
            
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
    
    async def _fallback_search(self, job_titles: List[str], keywords: List[str], page: int = 1) -> Dict[str, Any]:
        """
        Simplified fallback search with minimal filters
        """
        try:
            logger.info("Performing fallback search with minimal filters")
            
            # Use only the most basic filters
            filters = []
            
            # Just use broad job titles
            if job_titles:
                broad_titles = ["Software Engineer", "Backend Engineer", "Python Developer", "Software Developer", "Engineer"]
                filters.append({
                    "filter_type": "CURRENT_TITLE",
                    "type": "in",
                    "value": broad_titles
                })
            
            # Use only Python as keyword if it's in the list
            if keywords and any('python' in k.lower() for k in keywords):
                filters.append({
                    "filter_type": "KEYWORD",
                    "type": "in",
                    "value": ["Python"]
                })
            
            payload = {
                "filters": filters,
                "page": page
            }
            
            logger.info(f"Fallback search with filters: {filters}")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            data = response.json()
            
            profiles_found = len(data.get('profiles', []))
            logger.info(f"Fallback search found {profiles_found} candidates")
            
            return data
            
        except Exception as e:
            logger.error(f"Fallback search also failed: {str(e)}")
            return {"profiles": [], "message": "Both primary and fallback searches failed"}
    
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

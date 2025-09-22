import os
import json
from typing import Dict, Any
from openai import OpenAI
from utils.logger_config import setup_logging

logger = setup_logging()

class OpenAIJobParser:
    """Use OpenAI to intelligently parse job descriptions and generate CrustData API filters"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        try:
            # Initialize OpenAI client with explicit configuration
            self.client = OpenAI(
                api_key=api_key,
                timeout=30.0,
                max_retries=2
            )
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise ValueError(f"OpenAI client initialization failed: {str(e)}")
    
    def parse_job_description(self, job_description: str) -> Dict[str, Any]:
        """
        Use OpenAI to parse job description and generate optimal CrustData API filters
        
        Args:
            job_description: Raw job description text
            
        Returns:
            Dictionary with CrustData API compatible filters
        """
        try:
            logger.info("Using OpenAI to parse job description for optimal candidate search")
            
            # Create a detailed prompt for OpenAI
            prompt = self._create_parsing_prompt(job_description)
            
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert HR and recruitment AI assistant. Your job is to analyze job descriptions and extract the most relevant search criteria for finding candidates using the CrustData API."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=1000
            )
            
            # Parse the JSON response
            result_text = response.choices[0].message.content.strip()
            logger.info(f"OpenAI response: {result_text}")
            
            # Extract JSON from the response
            try:
                # Find JSON in the response (in case there's extra text)
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                json_str = result_text[start_idx:end_idx]
                
                parsed_result = json.loads(json_str)
                logger.info("Successfully parsed OpenAI response")
                
                return parsed_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI JSON response: {e}")
                logger.error(f"Raw response: {result_text}")
                # Fallback to basic parsing
                return self._fallback_parsing(job_description)
                
        except Exception as e:
            logger.error(f"Error using OpenAI for job parsing: {str(e)}")
            # Fallback to basic parsing
            return self._fallback_parsing(job_description)
    
    def _create_parsing_prompt(self, job_description: str) -> str:
        """Create a detailed prompt for OpenAI to parse the job description"""
        
        prompt = f"""
Analyze this job description and extract the optimal search criteria for finding candidates using the CrustData API.

Job Description:
{job_description}

Please return a JSON object with the following structure, using ONLY the exact values specified:

{{
    "job_titles": ["list of relevant job titles - be specific but not too narrow"],
    "functions": ["Engineering", "Information Technology"], // ONLY use these exact values
    "keywords": ["list of 3-5 most important technical skills/keywords"],
    "locations": ["list of locations mentioned, or 'United States' if not specified"],
    "experience_levels": ["experience level"], // MUST be one of: "Less than 1 year", "1 to 2 years", "3 to 5 years", "6 to 10 years", "More than 10 years"
    "search_strategy": "description of why these filters were chosen"
}}

IMPORTANT RULES:
1. For experience_levels, ONLY use these exact values: "Less than 1 year", "1 to 2 years", "3 to 5 years", "6 to 10 years", "More than 10 years"
2. For functions, ONLY use: "Engineering" or "Information Technology" 
3. For job_titles, include 2-4 relevant titles (e.g., "Software Engineer", "Python Developer", "Backend Engineer")
4. For keywords, focus on the 3-5 MOST important technical skills mentioned
5. For locations, extract specific locations or use "United States" as default
6. Be strategic - don't make filters too restrictive or you'll get no results

Return ONLY the JSON object, no additional text.
"""
        return prompt
    
    def _fallback_parsing(self, job_description: str) -> Dict[str, Any]:
        """Fallback parsing if OpenAI fails"""
        logger.info("Using fallback parsing method")
        
        text = job_description.lower()
        
        # Basic keyword extraction
        keywords = []
        tech_skills = ['python', 'django', 'fastapi', 'aws', 'docker', 'kubernetes', 'postgresql', 'redis', 'git', 'rest', 'api']
        for skill in tech_skills:
            if skill in text:
                keywords.append(skill)
        
        # Basic experience level detection
        experience_level = "3 to 5 years"  # Default
        if any(word in text for word in ['junior', 'entry', 'graduate', '0-2', '1-2']):
            experience_level = "1 to 2 years"
        elif any(word in text for word in ['senior', 'lead', '5+', '6+', '7+']):
            experience_level = "6 to 10 years"
        elif any(word in text for word in ['principal', 'staff', '10+']):
            experience_level = "More than 10 years"
        
        return {
            "job_titles": ["Software Engineer", "Python Developer"],
            "functions": ["Engineering", "Information Technology"],
            "keywords": keywords[:5],
            "locations": ["United States"],
            "experience_levels": [experience_level],
            "search_strategy": "Fallback parsing - basic keyword and pattern matching"
        }

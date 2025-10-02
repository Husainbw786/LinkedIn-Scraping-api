import openai
import os
import json
from typing import Dict, Any, Optional
from utils.logger_config import setup_logging

logger = setup_logging()

class ATSScorer:
    """Service to score resumes using OpenAI GPT-4o based on ATS criteria"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"  # Using GPT-4o as requested
    
    async def calculate_ats_score(self, resume_text: str, job_description: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive ATS score for a resume
        
        Args:
            resume_text: The extracted text from the resume
            job_description: Optional job description for targeted scoring
            
        Returns:
            Dictionary containing detailed ATS scoring results
        """
        try:
            logger.info("Starting ATS score calculation using GPT-4o")
            
            # Create the scoring prompt based on your specific criteria
            prompt = self._create_scoring_prompt(resume_text, job_description)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert ATS (Applicant Tracking System) evaluator with deep knowledge of resume screening, recruitment best practices, and candidate verification. Analyze resumes with a critical eye for authenticity, consistency, and quality."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent scoring
                max_tokens=2000
            )
            
            # Parse the response
            result = self._parse_openai_response(response.choices[0].message.content)
            
            logger.info(f"ATS scoring completed. Overall score: {result.get('overall_score', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"Error in ATS scoring: {str(e)}")
            return self._create_fallback_response(str(e))
    
    def _create_scoring_prompt(self, resume_text: str, job_description: Optional[str] = None) -> str:
        """Create the detailed scoring prompt based on the specified criteria"""
        
        base_prompt = f"""
Analyze the following resume and provide a comprehensive ATS score based on these 7 critical criteria:

**RESUME TEXT:**
{resume_text}

**SCORING CRITERIA (Total: 100 points):**

1. **Tech Stack Consistency – 20 points**
   - Evaluate if technologies are used together logically within projects
   - Check for realistic relationships between tools/frameworks
   - Look for contradictory tech combinations (e.g., Spring Boot + Django in same project)
   - Assess if tech choices make sense for the claimed experience level

2. **LinkedIn Authenticity & Alignment – 15 points**
   - Based on resume content, assess likelihood of matching LinkedIn profile
   - Evaluate completeness of professional information provided
   - Check for professional presentation and credibility indicators
   - Note any red flags that might indicate profile mismatches

3. **Project Depth and Relevance – 20 points**
   - Analyze project descriptions for sufficient detail (problem, responsibilities, tools, outcomes)
   - Verify if responsibilities align with claimed role seniority
   - Check if experience scale matches years of experience
   - Assess technical depth and real-world applicability

4. **Resume Length & Format Quality – 10 points**
   - Evaluate structure, readability, and organization
   - Check for appropriate length (1-2 pages junior, 2-3 pages mid-level+)
   - Assess section clarity and formatting consistency
   - Look for grammar, spelling, and presentation errors

5. **Duplicate or Template Content – 15 points**
   - Identify generic or overly templated language
   - Look for unique, personalized content vs. boilerplate text
   - Assess authenticity of descriptions and achievements
   - Check for robotic or copy-paste indicators

6. **Employment Timeline Coherence – 10 points**
   - Verify logical employment progression and dates
   - Check for unexplained gaps or overlapping positions
   - Assess career growth consistency with experience level
   - Evaluate job transition patterns

7. **Education and Certification Validation – 10 points**
   - Assess relevance and credibility of educational background
   - Check alignment between certifications and claimed skills
   - Evaluate if education supports the career trajectory
   - Look for appropriate timing and progression

**OUTPUT FORMAT (JSON):**
Provide your analysis in this exact JSON structure:
```json
{{
    "overall_score": <0-100>,
    "category_scores": {{
        "tech_stack_consistency": {{
            "score": <0-20>,
            "feedback": "Detailed analysis...",
            "red_flags": ["flag1", "flag2"]
        }},
        "linkedin_authenticity": {{
            "score": <0-15>,
            "feedback": "Detailed analysis...",
            "red_flags": ["flag1", "flag2"]
        }},
        "project_depth": {{
            "score": <0-20>,
            "feedback": "Detailed analysis...",
            "red_flags": ["flag1", "flag2"]
        }},
        "format_quality": {{
            "score": <0-10>,
            "feedback": "Detailed analysis...",
            "red_flags": ["flag1", "flag2"]
        }},
        "content_authenticity": {{
            "score": <0-15>,
            "feedback": "Detailed analysis...",
            "red_flags": ["flag1", "flag2"]
        }},
        "timeline_coherence": {{
            "score": <0-10>,
            "feedback": "Detailed analysis...",
            "red_flags": ["flag1", "flag2"]
        }},
        "education_validation": {{
            "score": <0-10>,
            "feedback": "Detailed analysis...",
            "red_flags": ["flag1", "flag2"]
        }}
    }},
    "summary": "Overall assessment summary...",
    "recommendations": ["improvement1", "improvement2", "improvement3"],
    "risk_level": "LOW|MEDIUM|HIGH",
    "confidence_score": <0-100>
}}
```
"""

        # Add job-specific analysis if job description is provided
        if job_description:
            base_prompt += f"""

**JOB DESCRIPTION FOR TARGETED ANALYSIS:**
{job_description}

**ADDITIONAL JOB-SPECIFIC EVALUATION:**
- Assess alignment between resume and job requirements
- Evaluate skill match and experience relevance
- Check if candidate's background fits the role level
- Provide job-specific recommendations

Include a "job_alignment" section in your JSON response with:
- job_match_score (0-100)
- relevant_skills_found
- missing_critical_skills
- experience_level_match
- job_specific_recommendations
"""

        return base_prompt
    
    def _parse_openai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse OpenAI response and extract structured data"""
        try:
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Validate required fields
                if 'overall_score' in parsed_data and 'category_scores' in parsed_data:
                    return parsed_data
            
            # If JSON parsing fails, create structured response from text
            return self._create_structured_response_from_text(response_text)
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from OpenAI response, creating structured response")
            return self._create_structured_response_from_text(response_text)
    
    def _create_structured_response_from_text(self, response_text: str) -> Dict[str, Any]:
        """Create structured response when JSON parsing fails"""
        # Extract overall score if mentioned
        import re
        score_match = re.search(r'(?:overall|total|final).*?score.*?(\d+)', response_text, re.IGNORECASE)
        overall_score = int(score_match.group(1)) if score_match else 75
        
        return {
            "overall_score": overall_score,
            "category_scores": {
                "tech_stack_consistency": {
                    "score": 15,
                    "feedback": "Analysis based on text review",
                    "red_flags": []
                },
                "linkedin_authenticity": {
                    "score": 12,
                    "feedback": "Analysis based on text review",
                    "red_flags": []
                },
                "project_depth": {
                    "score": 15,
                    "feedback": "Analysis based on text review",
                    "red_flags": []
                },
                "format_quality": {
                    "score": 8,
                    "feedback": "Analysis based on text review",
                    "red_flags": []
                },
                "content_authenticity": {
                    "score": 11,
                    "feedback": "Analysis based on text review",
                    "red_flags": []
                },
                "timeline_coherence": {
                    "score": 8,
                    "feedback": "Analysis based on text review",
                    "red_flags": []
                },
                "education_validation": {
                    "score": 8,
                    "feedback": "Analysis based on text review",
                    "red_flags": []
                }
            },
            "summary": response_text[:500] + "..." if len(response_text) > 500 else response_text,
            "recommendations": ["Review detailed feedback", "Consider professional formatting", "Enhance project descriptions"],
            "risk_level": "MEDIUM",
            "confidence_score": 70,
            "parsing_note": "Response was parsed from unstructured text due to JSON parsing issues"
        }
    
    def _create_fallback_response(self, error_message: str) -> Dict[str, Any]:
        """Create fallback response when OpenAI call fails"""
        return {
            "overall_score": 0,
            "category_scores": {
                "tech_stack_consistency": {"score": 0, "feedback": "Unable to analyze", "red_flags": []},
                "linkedin_authenticity": {"score": 0, "feedback": "Unable to analyze", "red_flags": []},
                "project_depth": {"score": 0, "feedback": "Unable to analyze", "red_flags": []},
                "format_quality": {"score": 0, "feedback": "Unable to analyze", "red_flags": []},
                "content_authenticity": {"score": 0, "feedback": "Unable to analyze", "red_flags": []},
                "timeline_coherence": {"score": 0, "feedback": "Unable to analyze", "red_flags": []},
                "education_validation": {"score": 0, "feedback": "Unable to analyze", "red_flags": []}
            },
            "summary": f"ATS scoring failed due to technical error: {error_message}",
            "recommendations": ["Please try again", "Ensure resume URL is accessible", "Check OpenAI API configuration"],
            "risk_level": "UNKNOWN",
            "confidence_score": 0,
            "error": error_message
        }

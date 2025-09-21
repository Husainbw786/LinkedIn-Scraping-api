from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from utils.logger_config import setup_logging

logger = setup_logging()

class CandidateMatcher:
    """Service to match and rank candidates based on job requirements"""
    
    def __init__(self):
        # Scoring weights
        self.weights = {
            'skills_match': 0.40,      # 40% - Skills matching
            'title_match': 0.25,       # 25% - Job title alignment  
            'experience_match': 0.15,  # 15% - Experience level matching
            'summary_similarity': 0.10, # 10% - Summary/description similarity
            'location_match': 0.10     # 10% - Location preference
        }
    
    def rank_candidates(
        self, 
        candidates: List[Dict[str, Any]], 
        job_requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Rank candidates based on job requirements using weighted scoring
        
        Args:
            candidates: List of candidate profiles
            job_requirements: Parsed job requirements
            
        Returns:
            List of candidates with match scores and explanations
        """
        try:
            logger.info(f"Ranking {len(candidates)} candidates against job requirements")
            
            scored_candidates = []
            
            for candidate in candidates:
                score, explanation = self._calculate_match_score(candidate, job_requirements)
                
                candidate_copy = candidate.copy()
                candidate_copy['match_score'] = round(score, 2)
                candidate_copy['match_explanation'] = explanation
                
                scored_candidates.append(candidate_copy)
            
            # Sort by match score (highest first)
            scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)
            
            logger.info(f"Ranked candidates. Top score: {scored_candidates[0]['match_score'] if scored_candidates else 0}")
            
            return scored_candidates
            
        except Exception as e:
            logger.error(f"Error ranking candidates: {str(e)}")
            return candidates
    
    def _calculate_match_score(
        self, 
        candidate: Dict[str, Any], 
        job_requirements: Dict[str, Any]
    ) -> Tuple[float, str]:
        """
        Calculate overall match score for a candidate
        
        Args:
            candidate: Candidate profile
            job_requirements: Job requirements
            
        Returns:
            Tuple of (score, explanation)
        """
        try:
            scores = {}
            explanations = []
            
            # 1. Skills matching (40%)
            skills_score, skills_exp = self._calculate_skills_match(
                candidate.get('skills', []), 
                job_requirements.get('skills', []) + job_requirements.get('keywords', [])
            )
            scores['skills_match'] = skills_score
            explanations.append(skills_exp)
            
            # 2. Title matching (25%)
            title_score, title_exp = self._calculate_title_match(
                candidate.get('current_title', '') or candidate.get('default_position_title', ''),
                job_requirements.get('job_titles', [])
            )
            scores['title_match'] = title_score
            explanations.append(title_exp)
            
            # 3. Experience level matching (15%)
            exp_score, exp_exp = self._calculate_experience_match(
                candidate.get('years_of_experience', ''),
                job_requirements.get('experience_level', [])
            )
            scores['experience_match'] = exp_score
            explanations.append(exp_exp)
            
            # 4. Summary similarity (10%)
            summary_score, summary_exp = self._calculate_summary_similarity(
                candidate.get('summary', '') + ' ' + candidate.get('headline', ''),
                ' '.join(job_requirements.get('all_extracted_keywords', []))
            )
            scores['summary_similarity'] = summary_score
            explanations.append(summary_exp)
            
            # 5. Location matching (10%)
            location_score, location_exp = self._calculate_location_match(
                candidate.get('location', ''),
                job_requirements.get('location', [])
            )
            scores['location_match'] = location_score
            explanations.append(location_exp)
            
            # Calculate weighted total score
            total_score = sum(scores[key] * self.weights[key] for key in scores) * 100
            
            # Create explanation
            explanation = '; '.join([exp for exp in explanations if exp])
            
            return total_score, explanation
            
        except Exception as e:
            logger.error(f"Error calculating match score: {str(e)}")
            return 0.0, "Error calculating match score"
    
    def _calculate_skills_match(self, candidate_skills: List[str], required_skills: List[str]) -> Tuple[float, str]:
        """Calculate skills matching score"""
        try:
            if not required_skills or not candidate_skills:
                return 0.0, "No skills data available"
            
            # Normalize skills to lowercase for comparison
            candidate_skills_lower = [skill.lower().strip() for skill in candidate_skills]
            required_skills_lower = [skill.lower().strip() for skill in required_skills]
            
            # Find matching skills
            matched_skills = []
            for req_skill in required_skills_lower:
                for cand_skill in candidate_skills_lower:
                    if req_skill in cand_skill or cand_skill in req_skill:
                        matched_skills.append(req_skill)
                        break
            
            # Calculate score
            if len(required_skills_lower) == 0:
                score = 0.0
            else:
                score = len(matched_skills) / len(required_skills_lower)
            
            explanation = f"Skills match: {len(matched_skills)}/{len(required_skills_lower)} required skills"
            
            return min(score, 1.0), explanation
            
        except Exception as e:
            logger.error(f"Error calculating skills match: {str(e)}")
            return 0.0, "Error in skills matching"
    
    def _calculate_title_match(self, candidate_title: str, required_titles: List[str]) -> Tuple[float, str]:
        """Calculate job title matching score"""
        try:
            if not required_titles or not candidate_title:
                return 0.5, "No title data available"  # Neutral score
            
            candidate_title_lower = candidate_title.lower().strip()
            
            # Check for exact or partial matches
            best_match_score = 0.0
            best_match_title = ""
            
            for req_title in required_titles:
                req_title_lower = req_title.lower().strip()
                
                # Exact match
                if candidate_title_lower == req_title_lower:
                    best_match_score = 1.0
                    best_match_title = req_title
                    break
                
                # Partial match - check if key words overlap
                candidate_words = set(candidate_title_lower.split())
                required_words = set(req_title_lower.split())
                
                if candidate_words and required_words:
                    overlap = len(candidate_words.intersection(required_words))
                    total_words = len(required_words)
                    
                    if total_words > 0:
                        match_score = overlap / total_words
                        if match_score > best_match_score:
                            best_match_score = match_score
                            best_match_title = req_title
            
            explanation = f"Title match: '{candidate_title}' vs required titles"
            if best_match_title:
                explanation += f" (best match: '{best_match_title}')"
            
            return best_match_score, explanation
            
        except Exception as e:
            logger.error(f"Error calculating title match: {str(e)}")
            return 0.5, "Error in title matching"
    
    def _calculate_experience_match(self, candidate_exp: str, required_exp: List[str]) -> Tuple[float, str]:
        """Calculate experience level matching score"""
        try:
            if not required_exp or not candidate_exp:
                return 0.5, "No experience data available"  # Neutral score
            
            # Map experience levels to numeric ranges for comparison
            exp_mapping = {
                "0 to 2 years": (0, 2),
                "2 to 6 years": (2, 6), 
                "6 to 10 years": (6, 10),
                "more than 10 years": (10, 20)
            }
            
            candidate_exp_lower = candidate_exp.lower().strip()
            candidate_range = exp_mapping.get(candidate_exp_lower, (3, 7))  # Default mid-level
            
            best_match_score = 0.0
            
            for req_exp in required_exp:
                req_exp_lower = req_exp.lower().strip()
                req_range = exp_mapping.get(req_exp_lower, (3, 7))
                
                # Calculate overlap between ranges
                overlap_start = max(candidate_range[0], req_range[0])
                overlap_end = min(candidate_range[1], req_range[1])
                
                if overlap_end > overlap_start:
                    # There's overlap
                    overlap_size = overlap_end - overlap_start
                    req_range_size = req_range[1] - req_range[0]
                    
                    if req_range_size > 0:
                        match_score = overlap_size / req_range_size
                        best_match_score = max(best_match_score, match_score)
            
            explanation = f"Experience match: {candidate_exp} vs required levels"
            
            return min(best_match_score, 1.0), explanation
            
        except Exception as e:
            logger.error(f"Error calculating experience match: {str(e)}")
            return 0.5, "Error in experience matching"
    
    def _calculate_summary_similarity(self, candidate_summary: str, job_keywords: str) -> Tuple[float, str]:
        """Calculate similarity between candidate summary and job keywords using TF-IDF"""
        try:
            if not candidate_summary.strip() or not job_keywords.strip():
                return 0.0, "No summary data available"
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
            
            documents = [candidate_summary.lower(), job_keywords.lower()]
            tfidf_matrix = vectorizer.fit_transform(documents)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            explanation = f"Summary similarity: {similarity:.2f} based on keyword overlap"
            
            return similarity, explanation
            
        except Exception as e:
            logger.error(f"Error calculating summary similarity: {str(e)}")
            return 0.0, "Error in summary matching"
    
    def _calculate_location_match(self, candidate_location: str, required_locations: List[str]) -> Tuple[float, str]:
        """Calculate location matching score"""
        try:
            if not required_locations or not candidate_location:
                return 0.5, "No location data available"  # Neutral score
            
            candidate_location_lower = candidate_location.lower().strip()
            
            # Check for matches
            for req_location in required_locations:
                req_location_lower = req_location.lower().strip()
                
                # Exact match
                if candidate_location_lower == req_location_lower:
                    return 1.0, f"Location match: {candidate_location}"
                
                # Partial match (city, state, country)
                candidate_parts = set(candidate_location_lower.split(','))
                required_parts = set(req_location_lower.split(','))
                
                # Remove empty strings and strip whitespace
                candidate_parts = {part.strip() for part in candidate_parts if part.strip()}
                required_parts = {part.strip() for part in required_parts if part.strip()}
                
                if candidate_parts and required_parts:
                    overlap = len(candidate_parts.intersection(required_parts))
                    if overlap > 0:
                        score = overlap / len(required_parts)
                        return score, f"Partial location match: {candidate_location}"
            
            # Check for remote work
            if 'remote' in candidate_location_lower and any('remote' in loc.lower() for loc in required_locations):
                return 1.0, "Remote work match"
            
            return 0.2, f"Location mismatch: {candidate_location}"
            
        except Exception as e:
            logger.error(f"Error calculating location match: {str(e)}")
            return 0.5, "Error in location matching"

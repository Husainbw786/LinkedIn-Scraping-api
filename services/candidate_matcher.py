from typing import List, Dict, Set
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging

from models.schemas import JobDescription, CandidateProfile

# Setup logger
logger = logging.getLogger(__name__)

class CandidateMatcher:
    """Match and rank candidates based on job requirements"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2)
        )
        
        # Weight factors for different matching criteria
        self.weights = {
            'skills_match': 0.4,
            'title_match': 0.25,
            'experience_level': 0.15,
            'summary_similarity': 0.1,
            'open_to_work_bonus': 0.1
        }
    
    def rank_candidates(self, job_desc: JobDescription, candidates: List[CandidateProfile]) -> List[CandidateProfile]:
        """
        Rank candidates based on job requirements compatibility
        Returns candidates sorted by match score (highest first)
        """
        if not candidates:
            return []
        
        logger.info(f"Ranking {len(candidates)} candidates against job: {job_desc.title}")
        
        # Calculate match scores for each candidate
        for candidate in candidates:
            candidate.match_score = self._calculate_match_score(job_desc, candidate)
            candidate.matched_skills = self._get_matched_skills(job_desc, candidate)
        
        # Sort by match score (descending)
        ranked_candidates = sorted(candidates, key=lambda x: x.match_score, reverse=True)
        
        if ranked_candidates:
            logger.info(f"Top candidate match: {ranked_candidates[0].name} - {ranked_candidates[0].headline} (Score: {ranked_candidates[0].match_score:.2f})")
        
        return ranked_candidates
    
    def _calculate_match_score(self, job_desc: JobDescription, candidate: CandidateProfile) -> float:
        """Calculate overall match score between job and candidate"""
        
        # 1. Skills matching
        skills_score = self._calculate_skills_match(job_desc, candidate)
        
        # 2. Job title/position matching
        title_score = self._calculate_title_match(job_desc, candidate)
        
        # 3. Experience level matching
        exp_score = self._calculate_experience_match(job_desc.experience_level, candidate.experience_level)
        
        # 4. Summary/description similarity
        summary_score = self._calculate_summary_similarity(job_desc, candidate)
        
        # 5. Open to work bonus
        open_to_work_score = 100.0 if candidate.is_open_to_work else 50.0
        
        # Calculate weighted total
        total_score = (
            skills_score * self.weights['skills_match'] +
            title_score * self.weights['title_match'] +
            exp_score * self.weights['experience_level'] +
            summary_score * self.weights['summary_similarity'] +
            open_to_work_score * self.weights['open_to_work_bonus']
        )
        
        return min(100.0, total_score)  # Cap at 100
    
    def _calculate_skills_match(self, job_desc: JobDescription, candidate: CandidateProfile) -> float:
        """Calculate skills matching score"""
        all_required_skills = job_desc.required_skills + job_desc.preferred_skills
        
        if not all_required_skills or not candidate.skills:
            return 30.0  # Neutral score if no skills data
        
        # Convert to lowercase for comparison
        required_skills_lower = [skill.lower() for skill in all_required_skills]
        candidate_skills_lower = [skill.lower() for skill in candidate.skills]
        
        # Calculate matches
        matched_skills = 0
        required_matches = 0
        preferred_matches = 0
        
        # Check required skills
        for skill in [s.lower() for s in job_desc.required_skills]:
            if skill in candidate_skills_lower:
                required_matches += 1
                matched_skills += 1
        
        # Check preferred skills
        for skill in [s.lower() for s in job_desc.preferred_skills]:
            if skill in candidate_skills_lower:
                preferred_matches += 1
                matched_skills += 1
        
        # Calculate score with higher weight for required skills
        required_score = 0
        if job_desc.required_skills:
            required_score = (required_matches / len(job_desc.required_skills)) * 80
        
        preferred_score = 0
        if job_desc.preferred_skills:
            preferred_score = (preferred_matches / len(job_desc.preferred_skills)) * 20
        
        total_score = required_score + preferred_score
        
        # Bonus for having many matched skills
        if matched_skills >= 5:
            total_score *= 1.2
        elif matched_skills >= 3:
            total_score *= 1.1
        
        return min(100.0, total_score)
    
    def _calculate_title_match(self, job_desc: JobDescription, candidate: CandidateProfile) -> float:
        """Calculate job title/position matching score"""
        job_title_lower = job_desc.title.lower()
        
        # Check current position
        if candidate.current_position:
            current_pos_lower = candidate.current_position.lower()
            if self._titles_match(job_title_lower, current_pos_lower):
                return 100.0
        
        # Check headline
        if candidate.headline:
            headline_lower = candidate.headline.lower()
            if self._titles_match(job_title_lower, headline_lower):
                return 90.0
        
        # Extract keywords and check for partial matches
        job_keywords = self._extract_job_keywords(job_title_lower)
        
        candidate_keywords = []
        if candidate.current_position:
            candidate_keywords.extend(self._extract_job_keywords(candidate.current_position.lower()))
        if candidate.headline:
            candidate_keywords.extend(self._extract_job_keywords(candidate.headline.lower()))
        
        if not job_keywords or not candidate_keywords:
            return 40.0
        
        common_keywords = set(job_keywords) & set(candidate_keywords)
        match_score = (len(common_keywords) / len(job_keywords)) * 100
        
        return min(100.0, match_score)
    
    def _titles_match(self, title1: str, title2: str) -> bool:
        """Check if two job titles match"""
        # Direct substring match
        if title1 in title2 or title2 in title1:
            return True
        
        # Check for common variations
        title1_clean = self._clean_title(title1)
        title2_clean = self._clean_title(title2)
        
        return title1_clean == title2_clean
    
    def _clean_title(self, title: str) -> str:
        """Clean job title for comparison"""
        # Remove common prefixes/suffixes
        title = re.sub(r'\b(senior|junior|lead|principal|staff|entry|level)\b', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\b(i|ii|iii|iv|v|1|2|3|4|5)\b', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        return title
    
    def _calculate_experience_match(self, job_exp_level: str, candidate_exp_level: str) -> float:
        """Calculate experience level matching score"""
        exp_levels = {
            'entry': 1,
            'mid': 2,
            'senior': 3,
            'executive': 4
        }
        
        job_level = exp_levels.get(job_exp_level.lower(), 2)
        candidate_level = exp_levels.get(candidate_exp_level.lower(), 2)
        
        # Perfect match
        if job_level == candidate_level:
            return 100.0
        
        # Adjacent levels
        if abs(job_level - candidate_level) == 1:
            return 80.0
        
        # Two levels apart
        if abs(job_level - candidate_level) == 2:
            return 60.0
        
        # More than two levels apart
        return 30.0
    
    def _calculate_summary_similarity(self, job_desc: JobDescription, candidate: CandidateProfile) -> float:
        """Calculate text similarity between job description and candidate summary"""
        try:
            # Combine candidate text
            candidate_text = " ".join([
                candidate.headline or "",
                candidate.summary or "",
                " ".join(candidate.skills),
                candidate.current_position or ""
            ])
            
            if not candidate_text.strip() or not job_desc.description.strip():
                return 50.0  # Neutral score
            
            # Calculate TF-IDF similarity
            texts = [job_desc.description, candidate_text]
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return similarity * 100
            
        except Exception as e:
            logger.warning(f"Summary similarity calculation failed: {str(e)}")
            return 50.0  # Neutral score on error
    
    def _get_matched_skills(self, job_desc: JobDescription, candidate: CandidateProfile) -> List[str]:
        """Get list of skills that match between job and candidate"""
        all_job_skills = job_desc.required_skills + job_desc.preferred_skills
        
        if not all_job_skills or not candidate.skills:
            return []
        
        job_skills_lower = [skill.lower() for skill in all_job_skills]
        candidate_skills_lower = [skill.lower() for skill in candidate.skills]
        
        matched = []
        for i, job_skill in enumerate(all_job_skills):
            if job_skill.lower() in candidate_skills_lower:
                matched.append(job_skill)
        
        return matched
    
    def _extract_job_keywords(self, title: str) -> List[str]:
        """Extract meaningful keywords from job title"""
        # Common job keywords to look for
        keywords = [
            'engineer', 'developer', 'manager', 'analyst', 'scientist', 'architect',
            'designer', 'consultant', 'specialist', 'coordinator', 'director',
            'software', 'data', 'product', 'project', 'business', 'technical',
            'senior', 'junior', 'lead', 'principal', 'staff', 'full', 'stack',
            'frontend', 'backend', 'devops', 'machine', 'learning', 'artificial',
            'intelligence', 'cloud', 'security', 'mobile', 'web', 'api'
        ]
        
        found_keywords = []
        title_words = re.findall(r'\b\w+\b', title.lower())
        
        for word in title_words:
            if word in keywords:
                found_keywords.append(word)
        
        return found_keywords

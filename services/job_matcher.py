from typing import List, Dict, Set
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from loguru import logger

from models.schemas import ResumeData, JobResult

class JobMatcher:
    """Match and rank jobs based on resume data"""
    
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
            'description_similarity': 0.2,
            'experience_level': 0.1,
            'keyword_match': 0.05
        }
    
    def rank_jobs(self, resume_data: ResumeData, jobs: List[JobResult]) -> List[JobResult]:
        """
        Rank jobs based on resume compatibility
        Returns jobs sorted by match score (highest first)
        """
        if not jobs:
            return []
        
        logger.info(f"Ranking {len(jobs)} jobs against resume")
        
        # Calculate match scores for each job
        for job in jobs:
            job.match_score = self._calculate_match_score(resume_data, job)
            job.matched_keywords = self._get_matched_keywords(resume_data, job)
            job.required_skills = self._extract_job_skills(job.description)
        
        # Sort by match score (descending)
        ranked_jobs = sorted(jobs, key=lambda x: x.match_score, reverse=True)
        
        logger.info(f"Top job match: {ranked_jobs[0].title} at {ranked_jobs[0].company} (Score: {ranked_jobs[0].match_score:.2f})")
        
        return ranked_jobs
    
    def _calculate_match_score(self, resume: ResumeData, job: JobResult) -> float:
        """Calculate overall match score between resume and job"""
        
        # 1. Skills matching
        skills_score = self._calculate_skills_match(resume.skills, job)
        
        # 2. Job title matching
        title_score = self._calculate_title_match(resume.job_titles, job.title)
        
        # 3. Description similarity
        desc_score = self._calculate_description_similarity(resume, job)
        
        # 4. Experience level matching
        exp_score = self._calculate_experience_match(resume.experience_level, job)
        
        # 5. Keyword matching
        keyword_score = self._calculate_keyword_match(resume.keywords, job)
        
        # Calculate weighted total
        total_score = (
            skills_score * self.weights['skills_match'] +
            title_score * self.weights['title_match'] +
            desc_score * self.weights['description_similarity'] +
            exp_score * self.weights['experience_level'] +
            keyword_score * self.weights['keyword_match']
        )
        
        return min(100.0, total_score)  # Cap at 100
    
    def _calculate_skills_match(self, resume_skills: List[str], job: JobResult) -> float:
        """Calculate skills matching score"""
        if not resume_skills:
            return 0.0
        
        job_text = f"{job.title} {job.description}".lower()
        resume_skills_lower = [skill.lower() for skill in resume_skills]
        
        matched_skills = 0
        for skill in resume_skills_lower:
            if skill in job_text:
                matched_skills += 1
        
        # Calculate percentage match with bonus for high matches
        match_percentage = (matched_skills / len(resume_skills)) * 100
        
        # Bonus for having many matched skills
        if matched_skills >= 5:
            match_percentage *= 1.2
        elif matched_skills >= 3:
            match_percentage *= 1.1
        
        return min(100.0, match_percentage)
    
    def _calculate_title_match(self, resume_titles: List[str], job_title: str) -> float:
        """Calculate job title matching score"""
        if not resume_titles:
            return 50.0  # Neutral score if no titles in resume
        
        job_title_lower = job_title.lower()
        resume_titles_lower = [title.lower() for title in resume_titles]
        
        # Direct matches
        for resume_title in resume_titles_lower:
            if resume_title in job_title_lower or job_title_lower in resume_title:
                return 100.0
        
        # Partial matches using common job keywords
        job_keywords = self._extract_job_keywords(job_title_lower)
        resume_keywords = []
        for title in resume_titles_lower:
            resume_keywords.extend(self._extract_job_keywords(title))
        
        if not job_keywords or not resume_keywords:
            return 30.0
        
        common_keywords = set(job_keywords) & set(resume_keywords)
        match_score = (len(common_keywords) / len(job_keywords)) * 100
        
        return min(100.0, match_score)
    
    def _calculate_description_similarity(self, resume: ResumeData, job: JobResult) -> float:
        """Calculate text similarity between resume content and job description"""
        try:
            # Combine resume text
            resume_text = " ".join([
                " ".join(resume.skills),
                " ".join(resume.job_titles),
                " ".join(resume.keywords),
                " ".join(resume.education),
                " ".join(resume.certifications)
            ])
            
            if not resume_text.strip() or not job.description.strip():
                return 30.0  # Neutral score
            
            # Calculate TF-IDF similarity
            texts = [resume_text, job.description]
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return similarity * 100
            
        except Exception as e:
            logger.warning(f"Description similarity calculation failed: {str(e)}")
            return 30.0
    
    def _calculate_experience_match(self, resume_level: str, job: JobResult) -> float:
        """Calculate experience level matching"""
        job_text = f"{job.title} {job.description}".lower()
        
        # Define experience level keywords
        level_keywords = {
            'entry': ['entry', 'junior', 'associate', 'graduate', 'intern', '0-2 years'],
            'mid': ['mid', 'intermediate', '2-5 years', '3-7 years'],
            'senior': ['senior', 'lead', 'principal', '5+ years', '7+ years'],
            'executive': ['director', 'vp', 'cto', 'ceo', 'executive', 'head of']
        }
        
        # Detect job level
        job_level = 'mid'  # Default
        for level, keywords in level_keywords.items():
            if any(keyword in job_text for keyword in keywords):
                job_level = level
                break
        
        # Calculate match score
        if resume_level == job_level:
            return 100.0
        elif abs(self._level_to_number(resume_level) - self._level_to_number(job_level)) == 1:
            return 70.0  # Adjacent levels
        else:
            return 30.0  # Far apart levels
    
    def _calculate_keyword_match(self, resume_keywords: List[str], job: JobResult) -> float:
        """Calculate keyword matching score"""
        if not resume_keywords:
            return 50.0
        
        job_text = f"{job.title} {job.description}".lower()
        resume_keywords_lower = [kw.lower() for kw in resume_keywords]
        
        matched_keywords = 0
        for keyword in resume_keywords_lower:
            if keyword in job_text:
                matched_keywords += 1
        
        return (matched_keywords / len(resume_keywords)) * 100
    
    def _get_matched_keywords(self, resume: ResumeData, job: JobResult) -> List[str]:
        """Get list of matched keywords between resume and job"""
        job_text = f"{job.title} {job.description}".lower()
        
        matched = []
        
        # Check skills
        for skill in resume.skills:
            if skill.lower() in job_text:
                matched.append(skill)
        
        # Check keywords
        for keyword in resume.keywords:
            if keyword.lower() in job_text and keyword not in matched:
                matched.append(keyword)
        
        return matched[:10]  # Return top 10 matches
    
    def _extract_job_skills(self, job_description: str) -> List[str]:
        """Extract technical skills from job description"""
        # Common technical skills patterns
        skill_patterns = [
            r'\b(?:python|java|javascript|react|angular|vue|node\.?js|express|django|flask)\b',
            r'\b(?:aws|azure|gcp|docker|kubernetes|jenkins|git)\b',
            r'\b(?:mysql|postgresql|mongodb|redis|elasticsearch)\b',
            r'\b(?:machine learning|data science|ai|ml|nlp|deep learning)\b',
            r'\b(?:agile|scrum|devops|ci/cd|microservices|api)\b'
        ]
        
        skills = []
        description_lower = job_description.lower()
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, description_lower, re.IGNORECASE)
            skills.extend(matches)
        
        return list(set(skills))  # Remove duplicates
    
    def _extract_job_keywords(self, text: str) -> List[str]:
        """Extract job-related keywords from text"""
        job_keywords = [
            'engineer', 'developer', 'analyst', 'manager', 'director',
            'senior', 'junior', 'lead', 'principal', 'staff',
            'software', 'data', 'product', 'project', 'technical',
            'full stack', 'backend', 'frontend', 'devops', 'qa'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in job_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _level_to_number(self, level: str) -> int:
        """Convert experience level to number for comparison"""
        level_map = {
            'entry': 1,
            'mid': 2,
            'senior': 3,
            'executive': 4
        }
        return level_map.get(level, 2)  # Default to mid-level

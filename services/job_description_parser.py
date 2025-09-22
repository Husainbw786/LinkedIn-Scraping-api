import re
import nltk
from typing import List, Dict, Any, Set
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
from utils.logger_config import setup_logging

logger = setup_logging()

class JobDescriptionParser:
    """Service to parse job descriptions and extract relevant information for candidate search"""
    
    def __init__(self):
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            nltk.download('punkt_tab')
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        
        from nltk.corpus import stopwords
        self.stop_words = set(stopwords.words('english'))
        
        # Common job titles and their variations
        self.job_title_patterns = {
            'backend': ['backend engineer', 'backend developer', 'server-side engineer', 'api developer'],
            'frontend': ['frontend engineer', 'frontend developer', 'ui developer', 'react developer'],
            'fullstack': ['fullstack engineer', 'full stack developer', 'full-stack engineer'],
            'senior': ['senior software engineer', 'senior developer', 'senior engineer', 'lead engineer'],
            'software': ['software engineer', 'software developer', 'programmer', 'developer'],
            'data': ['data engineer', 'data scientist', 'data analyst', 'ml engineer'],
            'devops': ['devops engineer', 'site reliability engineer', 'infrastructure engineer'],
            'mobile': ['mobile developer', 'ios developer', 'android developer', 'mobile engineer']
        }
        
        # Common technical skills
        self.tech_skills = {
            'python', 'java', 'javascript', 'typescript', 'go', 'golang', 'rust', 'c++', 'c#',
            'react', 'angular', 'vue', 'node.js', 'nodejs', 'express', 'django', 'flask',
            'fastapi', 'spring', 'laravel', 'rails', 'asp.net',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins',
            'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
            'git', 'github', 'gitlab', 'jira', 'confluence', 'slack',
            'machine learning', 'deep learning', 'ai', 'data science', 'analytics',
            'microservices', 'api', 'rest', 'graphql', 'grpc', 'websockets',
            'linux', 'unix', 'bash', 'shell', 'ci/cd', 'agile', 'scrum'
        }
        
        # Experience level indicators - mapped to CrustData API values
        self.experience_indicators = {
            'entry': ['entry level', 'junior', 'graduate', 'fresh', '0-2 years', '1-2 years'],
            'mid': ['mid level', 'intermediate', '2-5 years', '3-5 years', '2-6 years'],
            'senior': ['senior', 'lead', '5+ years', '5-10 years', '6+ years', 'experienced'],
            'executive': ['principal', 'staff', 'architect', '10+ years', 'director', 'vp']
        }
        
        # CrustData API experience level mapping
        self.crustdata_experience_mapping = {
            'entry': ['Less than 1 year', '1 to 2 years'],
            'mid': ['3 to 5 years'],
            'senior': ['6 to 10 years'],
            'executive': ['More than 10 years']
        }
        
        # Common functions/departments - using CrustData API valid values
        self.functions = [
            'Engineering', 'Information Technology'
        ]
    
    def parse_job_description(self, job_description: str) -> Dict[str, Any]:
        """
        Parse job description and extract relevant information for candidate search
        
        Args:
            job_description: Raw job description text
            
        Returns:
            Dictionary containing extracted information
        """
        try:
            logger.info("Parsing job description for candidate search")
            
            # Clean and normalize text
            cleaned_text = self._clean_text(job_description)
            
            # Extract different components
            job_titles = self._extract_job_titles(cleaned_text)
            skills = self._extract_skills(cleaned_text)
            experience_level = self._extract_experience_level(cleaned_text)
            functions = self._extract_functions(cleaned_text)
            keywords = self._extract_keywords(cleaned_text)
            location = self._extract_location(cleaned_text)
            
            result = {
                'job_titles': job_titles,
                'skills': skills,
                'experience_level': experience_level,
                'functions': functions,
                'keywords': keywords,
                'location': location,
                'all_extracted_keywords': list(set(skills + keywords))
            }
            
            logger.info(f"Extracted: {len(job_titles)} job titles, {len(skills)} skills, {len(keywords)} keywords")
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing job description: {str(e)}")
            raise Exception(f"Failed to parse job description: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep important ones
        text = re.sub(r'[^\w\s\-\+\#\.]', ' ', text)
        
        return text.strip()
    
    def _extract_job_titles(self, text: str) -> List[str]:
        """Extract relevant job titles from the text"""
        job_titles = []
        
        # Look for explicit job title patterns
        for category, titles in self.job_title_patterns.items():
            for title in titles:
                if title in text:
                    job_titles.append(title.title())
        
        # Look for common patterns like "seeking a [title]" or "looking for [title]"
        title_patterns = [
            r'seeking\s+(?:a\s+)?([a-zA-Z\s]+?)(?:\s+to|\s+who|\s+with)',
            r'looking\s+for\s+(?:a\s+)?([a-zA-Z\s]+?)(?:\s+to|\s+who|\s+with)',
            r'hiring\s+(?:a\s+)?([a-zA-Z\s]+?)(?:\s+to|\s+who|\s+with)',
            r'position:\s*([a-zA-Z\s]+?)(?:\n|\r|$)',
            r'role:\s*([a-zA-Z\s]+?)(?:\n|\r|$)'
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                title = match.strip().title()
                if len(title.split()) <= 4:  # Reasonable title length
                    job_titles.append(title)
        
        # Remove duplicates and return
        return list(set(job_titles))
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills from the text"""
        found_skills = []
        
        # Look for exact matches of known skills
        for skill in self.tech_skills:
            if skill.lower() in text:
                found_skills.append(skill)
        
        # Look for programming languages with common patterns
        prog_lang_patterns = [
            r'\b(python|java|javascript|typescript|go|golang|rust|c\+\+|c#|php|ruby|swift|kotlin)\b',
            r'\b(react|angular|vue|node\.?js|express|django|flask|spring|laravel)\b',
            r'\b(aws|azure|gcp|docker|kubernetes|terraform|jenkins|git)\b',
            r'\b(mysql|postgresql|mongodb|redis|elasticsearch)\b'
        ]
        
        for pattern in prog_lang_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_skills.extend([match.lower() for match in matches])
        
        # Remove duplicates
        return list(set(found_skills))
    
    def _extract_experience_level(self, text: str) -> List[str]:
        """Extract experience level requirements"""
        experience_levels = []
        
        # Look for explicit experience mentions
        for level, indicators in self.experience_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    # Use CrustData API compatible values
                    experience_levels.extend(self.crustdata_experience_mapping[level])
        
        # Look for numeric patterns
        year_patterns = [
            r'(\d+)\s*[-+]\s*years?\s+(?:of\s+)?experience',
            r'(\d+)\s*to\s*(\d+)\s*years?\s+(?:of\s+)?experience',
            r'minimum\s+(\d+)\s*years?\s+(?:of\s+)?experience'
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    min_years = int(match[0])
                else:
                    min_years = int(match)
                
                # Map to CrustData API values
                if min_years <= 1:
                    experience_levels.extend(["Less than 1 year", "1 to 2 years"])
                elif min_years <= 2:
                    experience_levels.extend(["1 to 2 years", "3 to 5 years"])
                elif min_years <= 5:
                    experience_levels.append("3 to 5 years")
                elif min_years <= 10:
                    experience_levels.append("6 to 10 years")
                else:
                    experience_levels.append("More than 10 years")
        
        # Default to mid-level if nothing found
        if not experience_levels:
            experience_levels = ["3 to 5 years", "6 to 10 years"]
        
        return list(set(experience_levels))
    
    def _extract_functions(self, text: str) -> List[str]:
        """Extract relevant functions/departments"""
        found_functions = []
        
        for function in self.functions:
            if function.lower() in text:
                found_functions.append(function)
        
        # Default functions for tech roles
        if not found_functions:
            found_functions = ["Engineering", "Information Technology"]
        
        return found_functions
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords using TF-IDF"""
        try:
            # Tokenize and remove stop words
            words = nltk.word_tokenize(text)
            words = [word for word in words if word.lower() not in self.stop_words and len(word) > 2]
            
            # Use TF-IDF to find important terms
            if len(words) > 10:
                vectorizer = TfidfVectorizer(max_features=20, ngram_range=(1, 2))
                tfidf_matrix = vectorizer.fit_transform([' '.join(words)])
                feature_names = vectorizer.get_feature_names_out()
                
                # Get top keywords
                scores = tfidf_matrix.toarray()[0]
                keyword_scores = list(zip(feature_names, scores))
                keyword_scores.sort(key=lambda x: x[1], reverse=True)
                
                keywords = [kw[0] for kw in keyword_scores[:10] if kw[1] > 0.1]
            else:
                keywords = words[:10]
            
            return keywords
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []
    
    def _extract_location(self, text: str) -> List[str]:
        """Extract location information"""
        # Common location patterns
        location_patterns = [
            r'location:\s*([a-zA-Z\s,]+?)(?:\n|\r|$)',
            r'based\s+in\s+([a-zA-Z\s,]+?)(?:\s|$)',
            r'office\s+in\s+([a-zA-Z\s,]+?)(?:\s|$)',
            r'remote\s+from\s+([a-zA-Z\s,]+?)(?:\s|$)'
        ]
        
        locations = []
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                location = match.strip().title()
                if len(location.split()) <= 5:  # Reasonable location length
                    locations.append(location)
        
        # Check for remote work
        if 'remote' in text:
            locations.append('Remote')
        
        # Default to USA if no location found
        if not locations:
            locations = ["United States"]
        
        return list(set(locations))

#!/usr/bin/env python3
"""
Direct test of the candidate scraper to debug the issue
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.candidate_scraper import LinkedInCandidateScaper

async def test_candidate_scraper():
    """Test the candidate scraper directly"""
    
    scraper = LinkedInCandidateScaper()
    
    print("🧪 Testing Candidate Scraper Directly")
    print("=" * 50)
    
    try:
        # Test with simple parameters
        candidates = await scraper.search_candidates(
            skills=["Python", "Django"],
            job_title="Python Developer",
            location="San Francisco, CA",
            experience_level="mid",
            max_results=3
        )
        
        print(f"✅ Found {len(candidates)} candidates")
        
        for i, candidate in enumerate(candidates, 1):
            print(f"\n🏆 Candidate #{i}:")
            print(f"   Name: {candidate.name}")
            print(f"   Headline: {candidate.headline}")
            print(f"   Skills: {candidate.skills}")
            print(f"   Location: {candidate.location}")
            print(f"   Company: {candidate.company}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_mock_generation():
    """Test mock candidate generation directly"""
    
    scraper = LinkedInCandidateScaper()
    
    print("\n🧪 Testing Mock Generation Directly")
    print("=" * 50)
    
    try:
        # Test the mock generation method directly
        query = 'site:linkedin.com/in "Python" "Django" "San Francisco, CA"'
        candidates = scraper._generate_mock_candidates(query, 3)
        
        print(f"✅ Generated {len(candidates)} mock candidates")
        
        for i, candidate in enumerate(candidates, 1):
            print(f"\n🏆 Mock Candidate #{i}:")
            print(f"   Name: {candidate.name}")
            print(f"   Headline: {candidate.headline}")
            print(f"   Skills: {candidate.skills}")
            print(f"   Location: {candidate.location}")
            print(f"   Company: {candidate.company}")
            
    except Exception as e:
        print(f"❌ Mock generation error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test mock generation first
    test_mock_generation()
    
    # Test full async scraper
    asyncio.run(test_candidate_scraper())

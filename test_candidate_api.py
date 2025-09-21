#!/usr/bin/env python3
"""
Test script for the new candidate finder API endpoint
"""

import requests
import json

# API endpoint
BASE_URL = "http://localhost:8000"
CANDIDATE_ENDPOINT = f"{BASE_URL}/api/v1/find-candidates"

def test_candidate_finder():
    """Test the candidate finder API with a sample job description"""
    
    # Sample job description
    job_description = """
    We are looking for a Senior Backend Engineer to join our growing team in San Francisco, CA.
    
    Requirements:
    - 5+ years of experience in backend development
    - Strong expertise in Python and Django/FastAPI
    - Experience with AWS cloud services (EC2, S3, RDS)
    - Knowledge of PostgreSQL and Redis
    - Experience with Docker and microservices architecture
    - Understanding of REST APIs and system design
    - Experience with CI/CD pipelines
    
    Preferred:
    - Experience with Kubernetes
    - Knowledge of machine learning frameworks
    - Previous startup experience
    
    Location: San Francisco, CA, United States
    Experience Level: Senior (5-10 years)
    """
    
    # Prepare request payload
    payload = {
        "job_description": job_description
    }
    
    try:
        print("🔍 Testing Candidate Finder API...")
        print(f"📍 Endpoint: {CANDIDATE_ENDPOINT}")
        print("📝 Job Description:")
        print("-" * 50)
        print(job_description)
        print("-" * 50)
        
        # Make API request
        response = requests.post(
            CANDIDATE_ENDPOINT,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            
            print("✅ API Response Successful!")
            print(f"📊 Total candidates found: {data.get('total_found', 0)}")
            print(f"🔑 Extracted keywords: {', '.join(data.get('extracted_keywords', [])[:10])}")
            
            # Display search filters
            filters = data.get('search_filters', {})
            print("\n🎯 Search Filters Applied:")
            for key, value in filters.items():
                if value:
                    print(f"  • {key.replace('_', ' ').title()}: {value}")
            
            # Display top candidates
            candidates = data.get('candidates', [])
            if candidates:
                print(f"\n👥 Top {min(3, len(candidates))} Candidates:")
                print("=" * 80)
                
                for i, candidate in enumerate(candidates[:3], 1):
                    print(f"\n{i}. {candidate.get('name', 'Unknown')}")
                    print(f"   📍 Location: {candidate.get('location', 'Not specified')}")
                    print(f"   💼 Current Title: {candidate.get('current_title', 'Not specified')}")
                    print(f"   🎯 Match Score: {candidate.get('match_score', 0):.1f}%")
                    print(f"   💡 Match Explanation: {candidate.get('match_explanation', 'N/A')}")
                    
                    # Display top skills
                    skills = candidate.get('skills', [])
                    if skills:
                        print(f"   🛠️  Top Skills: {', '.join(skills[:8])}")
                    
                    # LinkedIn profile
                    linkedin_url = candidate.get('linkedin_profile_url', '')
                    if linkedin_url:
                        print(f"   🔗 LinkedIn: {linkedin_url}")
                    
                    print("-" * 80)
            else:
                print("\n❌ No candidates found matching the criteria")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the API server is running on localhost:8000")
        print("💡 Start the server with: python main.py")
        
    except requests.exceptions.Timeout:
        print("⏰ Request Timeout: The API took too long to respond")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except:
        print("❌ Cannot connect to API server")
        return False

if __name__ == "__main__":
    print("🚀 LinkedIn Job Scraper & Candidate Finder API Test")
    print("=" * 60)
    
    # Test health endpoint first
    if test_health_endpoint():
        print()
        test_candidate_finder()
    else:
        print("\n💡 Please start the API server first:")
        print("   python main.py")
    
    print("\n" + "=" * 60)
    print("🏁 Test completed!")

#!/usr/bin/env python3
"""
Test script for the new candidate finder API endpoint
"""

import requests
import json
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_candidate_api():
    """Test the /api/v1/find-candidates endpoint"""
    
    # Test data - sample job description
    test_job_description = {
        "job_description": {
            "title": "Senior Python Developer",
            "company": "TechCorp Inc",
            "description": "We are looking for a Senior Python Developer with experience in Django, FastAPI, AWS, and machine learning. The ideal candidate should have 5+ years of experience building scalable web applications and working with databases like PostgreSQL. Knowledge of Docker, Kubernetes, and CI/CD pipelines is a plus.",
            "required_skills": ["Python", "Django", "FastAPI", "AWS", "PostgreSQL"],
            "preferred_skills": ["Docker", "Kubernetes", "Machine Learning", "CI/CD"],
            "experience_level": "senior",
            "location": "San Francisco, CA",
            "employment_type": "Full-time",
            "salary_range": "$120,000 - $180,000"
        },
        "max_results": 10
    }
    
    # API endpoint
    url = "http://localhost:8000/api/v1/find-candidates"
    
    try:
        print("🔍 Testing candidate finder API...")
        print(f"📋 Job: {test_job_description['job_description']['title']} at {test_job_description['job_description']['company']}")
        print(f"🎯 Required skills: {test_job_description['job_description']['required_skills']}")
        print(f"✨ Preferred skills: {test_job_description['job_description']['preferred_skills']}")
        print()
        
        # Make the API request
        response = requests.post(url, json=test_job_description, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ API call successful!")
            print(f"📊 Total candidates found: {data['total_found']}")
            print()
            
            # Display top candidates
            candidates = data['candidates'][:5]  # Show top 5
            
            for i, candidate in enumerate(candidates, 1):
                print(f"🏆 Candidate #{i} (Score: {candidate['match_score']:.1f}%)")
                print(f"   👤 Name: {candidate['name']}")
                print(f"   💼 Headline: {candidate['headline']}")
                print(f"   📍 Location: {candidate['location']}")
                print(f"   🏢 Company: {candidate.get('company', 'N/A')}")
                print(f"   🎯 Matched Skills: {', '.join(candidate['matched_skills'][:5])}")
                print(f"   🔗 Profile: {candidate['profile_url']}")
                print(f"   🚀 Open to work: {'Yes' if candidate['is_open_to_work'] else 'No'}")
                print()
            
            # Display search parameters
            search_params = data['search_parameters']
            print("🔧 Search Parameters:")
            print(f"   📍 Location: {search_params['location']}")
            print(f"   📊 Max results: {search_params['max_results']}")
            print(f"   🎓 Experience level: {search_params['experience_level']}")
            print(f"   🛠️ Skills searched: {', '.join(search_params['skills_searched'])}")
            
        else:
            print(f"❌ API call failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the API server is running on localhost:8000")
        print("💡 Run: uvicorn api.index:app --reload")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except:
        print("❌ Health check failed: Server not responding")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Root endpoint working")
            print(f"📝 Available endpoints: {list(data['endpoints'].keys())}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except:
        print("❌ Root endpoint failed: Server not responding")
        return False

if __name__ == "__main__":
    print("🧪 Testing LinkedIn Candidate Finder API")
    print("=" * 50)
    
    # Test basic endpoints first
    if test_health_endpoint() and test_root_endpoint():
        print()
        print("🎯 Testing candidate finder endpoint...")
        print("-" * 40)
        test_candidate_api()
    else:
        print("\n💡 Start the server with: uvicorn api.index:app --reload")

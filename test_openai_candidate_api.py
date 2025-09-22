#!/usr/bin/env python3
"""
Test script for the OpenAI-powered candidate finder API
"""

import requests
import json

# API endpoint
BASE_URL = "http://localhost:8000"
CANDIDATE_ENDPOINT = f"{BASE_URL}/api/v1/find-candidates"

def test_openai_candidate_finder():
    """Test the OpenAI-powered candidate finder API"""
    
    # Your original job description
    job_description = """
    BS degree in Computer Science, Software Engineering, or a related field (or equivalent experience).
    Proficiency in Python with strong programming and software development skills.
    3+ years of experience as a Python developer with hands-on experience in the Django framework.
    Experience developing RESTful APIs and asynchronous programming concepts with security and performance in mind.
    Background in developing virtualization solutions using technologies like QEMU and Docker.
    Experience with relational databases and SQL.
    Knowledge of version control systems (e.g., Git) and experience with agile development methodologies.
    Comfortable working in a fast-paced, highly collaborative environment.
    Strong verbal and written communication skills.
    """
    
    # Prepare request payload
    payload = {
        "job_description": job_description
    }
    
    try:
        print("🤖 Testing OpenAI-Powered Candidate Finder API...")
        print(f"📍 Endpoint: {CANDIDATE_ENDPOINT}")
        print("📝 Job Description:")
        print("-" * 80)
        print(job_description.strip())
        print("-" * 80)
        
        # Make API request
        print("\n🔄 Making API request...")
        response = requests.post(
            CANDIDATE_ENDPOINT,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120  # Increased timeout for OpenAI processing
        )
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            
            print("✅ API Response Successful!")
            print(f"📊 Total candidates found: {data.get('total_found', 0)}")
            
            # Display search filters and AI strategy
            filters = data.get('search_filters', {})
            print(f"\n🤖 AI Strategy: {filters.get('ai_strategy', 'Unknown')}")
            print(f"🎯 Filters Applied: {filters.get('filters_applied', 0)}")
            
            print("\n🔍 OpenAI Generated Filters:")
            for key, value in filters.items():
                if key not in ['ai_strategy', 'filters_applied'] and value:
                    print(f"  • {key.replace('_', ' ').title()}: {value}")
            
            # Display extracted keywords
            keywords = data.get('extracted_keywords', [])
            if keywords:
                print(f"\n🔑 Extracted Keywords: {', '.join(keywords)}")
            
            # Display top candidates
            candidates = data.get('candidates', [])
            if candidates:
                print(f"\n👥 Top {min(5, len(candidates))} Candidates:")
                print("=" * 100)
                
                for i, candidate in enumerate(candidates[:5], 1):
                    print(f"\n{i}. {candidate.get('name', 'Unknown')}")
                    print(f"   📍 Location: {candidate.get('location', 'Not specified')}")
                    print(f"   💼 Current Title: {candidate.get('current_title', 'Not specified')}")
                    print(f"   🎯 Match Score: {candidate.get('match_score', 0):.1f}%")
                    print(f"   💡 Match Explanation: {candidate.get('match_explanation', 'N/A')}")
                    
                    # Display top skills
                    skills = candidate.get('skills', [])
                    if skills:
                        print(f"   🛠️  Top Skills: {', '.join(skills[:10])}")
                    
                    # LinkedIn profile
                    linkedin_url = candidate.get('linkedin_profile_url', '')
                    if linkedin_url:
                        print(f"   🔗 LinkedIn: {linkedin_url}")
                    
                    # Years of experience
                    experience = candidate.get('years_of_experience', '')
                    if experience:
                        print(f"   📅 Experience: {experience}")
                    
                    print("-" * 100)
                    
                # Show summary statistics
                print(f"\n📈 Summary Statistics:")
                scores = [c.get('match_score', 0) for c in candidates]
                if scores:
                    print(f"   • Average Match Score: {sum(scores)/len(scores):.1f}%")
                    print(f"   • Highest Match Score: {max(scores):.1f}%")
                    print(f"   • Lowest Match Score: {min(scores):.1f}%")
                
            else:
                print("\n❌ No candidates found matching the criteria")
                print("💡 Try with a different job description or check the API logs")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error Details: {error_data}")
            except:
                print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the API server is running on localhost:8000")
        print("💡 Start the server with: python main.py")
        
    except requests.exceptions.Timeout:
        print("⏰ Request Timeout: The API took too long to respond (>120s)")
        print("💡 This might be due to OpenAI API processing time")
        
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
    print("🚀 OpenAI-Powered Candidate Finder API Test")
    print("=" * 80)
    
    # Test health endpoint first
    if test_health_endpoint():
        print()
        test_openai_candidate_finder()
    else:
        print("\n💡 Please start the API server first:")
        print("   python main.py")
        print("\n🔧 Make sure you have set the following environment variables:")
        print("   - CRUSTDATA_API_TOKEN")
        print("   - OPENAI_API_KEY")
    
    print("\n" + "=" * 80)
    print("🏁 Test completed!")

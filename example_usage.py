#!/usr/bin/env python3
"""
Example usage of the LinkedIn Candidate Finder API
"""

import requests
import json

def find_candidates_example():
    """Example of how to use the /api/v1/find-candidates endpoint"""
    
    # API endpoint
    url = "http://localhost:8000/api/v1/find-candidates"
    
    # Example 1: Full Stack Developer position
    job_request = {
        "job_description": {
            "title": "Full Stack Developer",
            "company": "StartupXYZ",
            "description": "We're looking for a talented Full Stack Developer to join our growing team. You'll work with React, Node.js, Python, and AWS to build scalable web applications. Experience with Docker and CI/CD is highly valued.",
            "required_skills": ["JavaScript", "React", "Node.js", "Python"],
            "preferred_skills": ["AWS", "Docker", "CI/CD", "TypeScript"],
            "experience_level": "mid",
            "location": "New York, NY",
            "employment_type": "Full-time"
        },
        "max_results": 15
    }
    
    try:
        print("🔍 Searching for Full Stack Developer candidates...")
        response = requests.post(url, json=job_request)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total_found']} candidates!")
            
            # Show top 3 candidates
            for i, candidate in enumerate(data['candidates'][:3], 1):
                print(f"\n🏆 Top Candidate #{i}")
                print(f"   Name: {candidate['name']}")
                print(f"   Score: {candidate['match_score']:.1f}%")
                print(f"   Headline: {candidate['headline']}")
                print(f"   Skills Match: {', '.join(candidate['matched_skills'])}")
                print(f"   Open to Work: {'Yes' if candidate['is_open_to_work'] else 'No'}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def find_data_scientist_candidates():
    """Example for Data Science position"""
    
    url = "http://localhost:8000/api/v1/find-candidates"
    
    # Example 2: Data Scientist position
    job_request = {
        "job_description": {
            "title": "Senior Data Scientist",
            "company": "DataCorp",
            "description": "Join our AI team to build machine learning models using Python, TensorFlow, and AWS. We need someone with strong statistical background and experience with big data technologies like Spark and Hadoop.",
            "required_skills": ["Python", "Machine Learning", "TensorFlow", "Statistics"],
            "preferred_skills": ["AWS", "Apache Spark", "Deep Learning", "PyTorch"],
            "experience_level": "senior",
            "location": "San Francisco, CA",
            "employment_type": "Full-time",
            "salary_range": "$140,000 - $200,000"
        },
        "max_results": 10
    }
    
    try:
        print("\n" + "="*50)
        print("🔍 Searching for Data Scientist candidates...")
        response = requests.post(url, json=job_request)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total_found']} candidates!")
            
            # Show candidates with high match scores
            high_match_candidates = [c for c in data['candidates'] if c['match_score'] > 50]
            
            print(f"\n🎯 High-match candidates (>50% score): {len(high_match_candidates)}")
            
            for candidate in high_match_candidates:
                print(f"\n   👤 {candidate['name']} ({candidate['match_score']:.1f}%)")
                print(f"      {candidate['headline']}")
                print(f"      Skills: {', '.join(candidate['matched_skills'][:5])}")
                print(f"      Profile: {candidate['profile_url']}")
                
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def minimal_job_description_example():
    """Example with minimal job description (auto skill extraction)"""
    
    url = "http://localhost:8000/api/v1/find-candidates"
    
    # Example 3: Minimal job description - let the API extract skills
    job_request = {
        "job_description": {
            "title": "DevOps Engineer",
            "company": "CloudTech Solutions",
            "description": "We need a DevOps Engineer experienced with Kubernetes, Docker, Jenkins, and AWS. You'll be responsible for CI/CD pipelines, infrastructure automation with Terraform, and monitoring production systems. Linux expertise is essential.",
            "experience_level": "mid",
            "location": "Austin, TX"
        },
        "max_results": 8
    }
    
    try:
        print("\n" + "="*50)
        print("🔍 Searching with auto skill extraction...")
        response = requests.post(url, json=job_request)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total_found']} candidates!")
            
            # Show what skills were auto-extracted
            job_summary = data['job_summary']
            print(f"\n🛠️ Auto-extracted skills:")
            print(f"   Required: {job_summary['required_skills']}")
            print(f"   Preferred: {job_summary['preferred_skills']}")
            
            # Show search parameters
            search_params = data['search_parameters']
            print(f"\n🔧 Search executed with:")
            print(f"   Skills: {', '.join(search_params['skills_searched'])}")
            print(f"   Location: {search_params['location']}")
            print(f"   Experience: {search_params['experience_level']}")
                
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🚀 LinkedIn Candidate Finder API - Usage Examples")
    print("=" * 60)
    
    # Run examples
    find_candidates_example()
    find_data_scientist_candidates()
    minimal_job_description_example()
    
    print("\n" + "="*60)
    print("💡 Tips:")
    print("   • Provide specific required_skills for better matching")
    print("   • Use preferred_skills for nice-to-have qualifications")
    print("   • The API auto-extracts skills if none provided")
    print("   • Candidates marked 'open to work' get bonus points")
    print("   • Higher match scores indicate better fit")
    print("\n📚 API Documentation: http://localhost:8000/docs")

#!/usr/bin/env python3
"""
Test script for the new simplified candidate finder API endpoint
"""

import requests
import json

def test_simple_candidate_api():
    """Test the /api/v1/find-candidates-simple endpoint"""
    
    # Real job description examples
    job_descriptions = [
        {
            "name": "Senior Python Developer",
            "text": """
Senior Python Developer - TechCorp Inc

We are looking for a Senior Python Developer to join our dynamic team. The ideal candidate will have 5+ years of experience with Python development and strong expertise in Django and FastAPI frameworks.

Key Requirements:
- 5+ years of Python development experience
- Strong experience with Django and FastAPI
- Knowledge of AWS cloud services
- Experience with PostgreSQL databases
- Docker and Kubernetes experience preferred
- CI/CD pipeline experience
- Strong problem-solving skills

Location: San Francisco, CA (Remote options available)
Salary: $120,000 - $180,000
Employment Type: Full-time

We offer competitive benefits, flexible work arrangements, and opportunities for professional growth.
            """,
            "company": "TechCorp Inc"
        },
        {
            "name": "Full Stack JavaScript Developer",
            "text": """
Full Stack Developer Opportunity

Join our startup as a Full Stack Developer! We're building the next generation of web applications and need someone passionate about modern JavaScript technologies.

What you'll do:
- Build responsive web applications using React and Node.js
- Work with our backend APIs and databases
- Collaborate with our design team on user experiences
- Deploy and maintain applications on cloud platforms

Requirements:
- 3+ years of JavaScript development
- Experience with React and Node.js
- Knowledge of MongoDB or PostgreSQL
- Familiarity with AWS or similar cloud platforms
- Experience with Git and modern development workflows

Nice to have:
- TypeScript experience
- Docker knowledge
- Experience with GraphQL
- Mobile development experience

Location: Austin, TX
Type: Full-time
Salary: $80,000 - $120,000
            """,
            "company": "StartupXYZ"
        },
        {
            "name": "Data Scientist",
            "text": """
Data Scientist - AI/ML Focus

We're seeking a talented Data Scientist to join our AI research team. You'll work on cutting-edge machine learning projects and help drive data-driven decision making across the organization.

Responsibilities:
- Develop and deploy machine learning models
- Analyze large datasets to extract insights
- Work with engineering teams to productionize models
- Present findings to stakeholders

Required Skills:
- PhD or Masters in Data Science, Statistics, or related field
- 4+ years of experience in machine learning
- Strong Python skills with pandas, numpy, scikit-learn
- Experience with TensorFlow or PyTorch
- SQL and database experience
- Statistical analysis expertise

Preferred:
- Experience with Apache Spark
- Cloud platform experience (AWS, GCP)
- Deep learning experience
- Experience with MLOps tools

Location: Remote (US timezone)
Compensation: $130,000 - $200,000 + equity
            """,
            "company": "DataCorp AI"
        }
    ]
    
    # API endpoint
    url = "http://localhost:8000/api/v1/find-candidates-simple"
    
    for job in job_descriptions:
        print(f"\n{'='*60}")
        print(f"🧪 Testing: {job['name']}")
        print(f"🏢 Company: {job['company']}")
        print("="*60)
        
        # Prepare request
        test_request = {
            "job_description_text": job["text"].strip(),
            "company": job["company"],
            "max_results": 8
        }
        
        try:
            print("🔍 Sending job description to API...")
            response = requests.post(url, json=test_request, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                print("✅ API call successful!")
                print(f"📊 Total candidates found: {data['total_found']}")
                
                # Show parsed job details
                job_summary = data['job_summary']
                print(f"\n🎯 Parsed Job Details:")
                print(f"   Title: {job_summary['title']}")
                print(f"   Experience Level: {job_summary['experience_level']}")
                print(f"   Location: {job_summary['location']}")
                print(f"   Required Skills: {', '.join(job_summary['required_skills'][:5])}")
                print(f"   Preferred Skills: {', '.join(job_summary['preferred_skills'][:5])}")
                
                # Show top candidates
                candidates = data['candidates'][:3]  # Top 3
                print(f"\n🏆 Top Candidates:")
                
                for i, candidate in enumerate(candidates, 1):
                    print(f"\n   #{i} {candidate['name']} (Score: {candidate['match_score']:.1f}%)")
                    print(f"      💼 {candidate['headline']}")
                    print(f"      📍 {candidate['location']}")
                    print(f"      🎯 Matched Skills: {', '.join(candidate['matched_skills'][:4])}")
                    print(f"      🚀 Open to work: {'Yes' if candidate['is_open_to_work'] else 'No'}")
                
                # Show search info
                search_params = data['search_parameters']
                print(f"\n🔧 Search Info:")
                print(f"   Parsing Method: {search_params.get('parsing_method', 'fallback')}")
                print(f"   Skills Searched: {', '.join(search_params['skills_searched'])}")
                
            else:
                print(f"❌ API call failed with status code: {response.status_code}")
                print(f"Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection error: Make sure the API server is running on localhost:8000")
            print("💡 Run: uvicorn api.index:app --reload")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

def test_minimal_input():
    """Test with very minimal input"""
    
    url = "http://localhost:8000/api/v1/find-candidates-simple"
    
    minimal_request = {
        "job_description_text": "Looking for a Python developer with Django experience for our startup in NYC. Must know AWS and Docker.",
        "max_results": 5
    }
    
    print(f"\n{'='*60}")
    print("🧪 Testing Minimal Input")
    print("="*60)
    
    try:
        response = requests.post(url, json=minimal_request, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            job_summary = data['job_summary']
            
            print("✅ Minimal input test successful!")
            print(f"📋 Extracted Title: {job_summary['title']}")
            print(f"🛠️ Extracted Skills: {job_summary['required_skills'] + job_summary['preferred_skills']}")
            print(f"📍 Extracted Location: {job_summary['location']}")
            print(f"👥 Found {data['total_found']} candidates")
            
        else:
            print(f"❌ Minimal test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Minimal test error: {str(e)}")

if __name__ == "__main__":
    print("🚀 Testing Simplified LinkedIn Candidate Finder API")
    print("This endpoint takes raw job description text and auto-extracts everything!")
    
    # Test main functionality
    test_simple_candidate_api()
    
    # Test minimal input
    test_minimal_input()
    
    print(f"\n{'='*60}")
    print("💡 Usage Tips:")
    print("   • Just paste any job description text - the API extracts everything automatically")
    print("   • Works with or without OpenAI API key (fallback parsing included)")
    print("   • Much simpler than the structured endpoint")
    print("   • Perfect for quick candidate searches")
    print("\n📚 Try it at: http://localhost:8000/docs")

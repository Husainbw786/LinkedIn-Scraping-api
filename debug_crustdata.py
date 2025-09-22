#!/usr/bin/env python3
"""
Debug script to test CrustData API directly with different filter combinations
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def test_crustdata_api():
    """Test CrustData API with different filter combinations"""
    
    api_token = os.getenv("CRUSTDATA_API_TOKEN")
    if not api_token:
        print("❌ CRUSTDATA_API_TOKEN not found in environment")
        return
    
    base_url = "https://api.crustdata.com/screener/person/search"
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }
    
    # Test different filter combinations
    test_cases = [
        {
            "name": "Minimal - Just Python keyword",
            "filters": [
                {"filter_type": "KEYWORD", "type": "in", "value": ["Python"]}
            ]
        },
        {
            "name": "Job titles only",
            "filters": [
                {"filter_type": "CURRENT_TITLE", "type": "in", "value": ["Software Engineer", "Python Developer"]}
            ]
        },
        {
            "name": "Functions only", 
            "filters": [
                {"filter_type": "FUNCTION", "type": "in", "value": ["Engineering", "Information Technology"]}
            ]
        },
        {
            "name": "Experience only (corrected)",
            "filters": [
                {"filter_type": "YEARS_OF_EXPERIENCE", "type": "in", "value": ["3 to 5 years"]}
            ]
        },
        {
            "name": "Your original filters (corrected)",
            "filters": [
                {"filter_type": "CURRENT_TITLE", "type": "in", "value": ["Software Engineer", "Python Developer"]},
                {"filter_type": "FUNCTION", "type": "in", "value": ["Engineering", "Information Technology"]},
                {"filter_type": "KEYWORD", "type": "in", "value": ["Python Django"]},
                {"filter_type": "YEARS_OF_EXPERIENCE", "type": "in", "value": ["3 to 5 years"]}
            ]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print("-" * 50)
        
        payload = {
            "filters": test_case["filters"],
            "page": 1
        }
        
        try:
            response = requests.post(
                base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                profiles = data.get('profiles', [])
                print(f"✅ Found {len(profiles)} candidates")
                
                if profiles:
                    # Show first candidate as example
                    first_candidate = profiles[0]
                    print(f"   Example: {first_candidate.get('name', 'Unknown')} - {first_candidate.get('current_title', 'No title')}")
                    print(f"   Location: {first_candidate.get('location', 'Unknown')}")
                else:
                    print("   No candidates returned")
                    
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🏁 Debug tests completed!")

if __name__ == "__main__":
    print("🔍 CrustData API Debug Tool")
    print("=" * 60)
    test_crustdata_api()

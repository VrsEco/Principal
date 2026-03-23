"""
Test script to directly call the section status API endpoint
"""
import requests

# Test closing the participants section
url = "http://127.0.0.1:5032/pev/v1/api/plans/43/sections/participants/close"

print(f"Testing POST to: {url}")
print("-" * 60)

try:
    response = requests.post(url, json={}, headers={'Content-Type': 'application/json'})
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            print(f"\nError Details: {error_data}")
        except:
            print("\nCould not parse error as JSON")
except Exception as e:
    print(f"Error making request: {e}")

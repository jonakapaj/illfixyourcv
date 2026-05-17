import requests
import os

url = "http://localhost:8000/analyze"
files = {'file': ('test.pdf', open('../job_description.txt', 'rb'), 'application/pdf')}
data = {
    'job_description': 'Test JD',
    'user_instructions': ''
}

try:
    response = requests.post(url, files=files, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json().keys()}")
except Exception as e:
    print(f"Error: {e}")

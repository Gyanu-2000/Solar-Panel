import requests

# Test the API
url = "http://127.0.0.1:5000/api/solar"
params = {"lat": 26.86, "lon": 81.03}

try:
    response = requests.get(url, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

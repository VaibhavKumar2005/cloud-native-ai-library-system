#!/usr/bin/env python
import requests
import json

response = requests.post('http://localhost:8000/api/token/', json={
    'username': 'testuser', 
    'password': 'testpass123'
})

if response.status_code == 200:
    data = response.json()
    print(f"Access Token:\n{data['access']}\n")
    print(f"Refresh Token:\n{data['refresh']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

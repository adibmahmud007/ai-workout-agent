# test_groq.py
import os
import requests # type: ignore
from dotenv import load_dotenv # type: ignore

load_dotenv()
key = os.getenv("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}


body = {
    "model": "llama3-8b-8192",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! Can you give me a short workout tip?"}
    ]
}

res = requests.post(url, headers=headers, json=body)

print("Status:", res.status_code)
print("Response:", res.json())

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load API settings from the project root .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

API_URL = "https://openrouter.ai/api/v1/chat/completions"


def ask_ai(prompt, system_prompt="You are an expert SEO and AEO assistant."):
    if not API_KEY:
        raise ValueError(
            "OpenRouter API key is missing. Check your .env file."
        )

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=90
    )

    if not response.ok:
        raise RuntimeError(
            f"OpenRouter API error ({response.status_code}): "
            f"{response.text[:1000]}"
        )

    result = response.json()
    return result["choices"][0]["message"]["content"]
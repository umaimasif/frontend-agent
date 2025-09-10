import os
import json
from litellm import completion
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your .env file")

# Strip quotes if accidentally added
GROQ_API_KEY = GROQ_API_KEY.strip('"').strip("'")

PROMPT_TEMPLATE = '''
You are an assistant that creates a complete frontend project for a website based on the user's description.
Produce a JSON object where keys are relative file paths and values are the file contents as strings.
The project should be a ready-to-run frontend (React with Tailwind, or simple HTML/CSS/JS if requested).

Rules:
- Output must be valid JSON only. No commentary.
- Keep files reasonable in size; avoid embedding large assets.
- Ensure imports are included in JSX files.

User request:
\"\"\"{user_prompt}\"\"\"
'''

def generate_project_from_prompt(user_prompt: str) -> Dict[str, str]:
    print("[DEBUG] User prompt:", user_prompt)

    prompt = PROMPT_TEMPLATE.format(user_prompt=user_prompt)

    print("[DEBUG] Calling Groq API...")
    response = completion(
        model="groq/llama-3.1-8b-instant",  # ✅ use a Groq-supported model
        messages=[
            {"role": "system", "content": "You are a helpful code generator that outputs only JSON mapping filenames to file contents."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=4000,
        api_key=GROQ_API_KEY  # ✅ pass the API key
    )

    text = response['choices'][0]['message']['content']
    print("[DEBUG] Raw response from Groq:", text[:500])  # first 500 chars

    # Try to parse JSON
    try:
        project_json = json.loads(text)
    except Exception:
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1:
            raise ValueError("[ERROR] Model did not return valid JSON. Raw output:\n" + text[:1000])
        raw = text[start:end+1]
        project_json = json.loads(raw)

    if not isinstance(project_json, dict):
        raise ValueError('[ERROR] Expected JSON object mapping filenames to contents')

    for k, v in list(project_json.items()):
        if not isinstance(v, str):
            project_json[k] = json.dumps(v)

    print("[DEBUG] Files returned from generator:", list(project_json.keys()))
    return project_json

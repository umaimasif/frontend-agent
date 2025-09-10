import os
import re
from litellm import completion
from dotenv import load_dotenv

# Load env vars
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your .env file")

PROMPT_TEMPLATE = """
You are a frontend code generator. 
Generate a complete {framework} project based on the description below.

Rules:
- Output only valid code blocks (no explanations).
- Use proper file structure markers like:
  --- filename ---
  (code here)
  --- end ---

User description:
\"\"\"{user_prompt}\"\"\"
"""

def generate_project_from_prompt(user_prompt: str, framework: str = "React + Tailwind") -> dict:
    """
    Generate frontend project code files from LLM response.
    Returns: dict mapping filename -> file content
    """
    print("[DEBUG] User prompt:", user_prompt)

    prompt = PROMPT_TEMPLATE.format(user_prompt=user_prompt, framework=framework)

    response = completion(
        model="groq/llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You output only code in structured blocks."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=4000
    )

    text = response["choices"][0]["message"]["content"]
    print("[DEBUG] Raw response preview:", text[:400])

    # Extract code blocks with filename markers
    files = {}
    pattern = r"---\s*(.*?)\s*---\n(.*?)---\s*end\s*---"
    matches = re.findall(pattern, text, re.DOTALL)

    if not matches:
        raise ValueError("No code blocks detected. Raw output:\n" + text[:500])

    for filename, content in matches:
        files[filename.strip()] = content.strip()

    print("[DEBUG] Files generated:", list(files.keys()))
    return files

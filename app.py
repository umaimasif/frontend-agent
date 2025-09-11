import os
import re
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from textwrap import dedent

import streamlit as st

# Try to import litellm lazily
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    completion = None
    LITELLM_AVAILABLE = False

# ---------------------
# Configuration
# ---------------------
OUTPUT_ROOT = Path("output")
OUTPUT_ROOT.mkdir(exist_ok=True, parents=True)

DEFAULT_GROQ_MODELS = [
    "groq/llama-3.3-70b-versatile",
    "groq/llama-3.1-8b-instant",
]

# ---------------------
# Utilities
# ---------------------
def timestamped_folder(base: Path, prefix: str = "project"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = base / f"{prefix}_{ts}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def make_zip_from_folder(folder: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in folder.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(folder))

def safe_extract_code_blocks(text: str):
    files = {}
    # Try --- filename --- ... --- end --- pattern
    pattern = r"---\s*(.*?)\s*---\n(.*?)---\s*end\s*---"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    if matches:
        for filename, content in matches:
            files[filename.strip()] = content.strip()
        return files

    # Fallback: markdown-style codeblocks
    codeblocks = re.findall(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    for i, cb in enumerate(codeblocks, 1):
        files[f"file_{i}.txt"] = cb.strip()

    # Fallback: HTML detection
    if not files and ("<html" in text.lower() or "<!doctype html" in text.lower()):
        files["index.html"] = text.strip()

    return files

# ---------------------
# Mock generator
# ---------------------
def mock_generator(user_prompt: str, framework: str):
    if "react" in framework.lower():
        # React App JSX code as plain string
        app_jsx = """
import React from 'react';

export default function App() {
  return (
    <div className="app" style={{ padding: 24, fontFamily: 'Arial' }}>
      <header style={{ textAlign: 'center' }}>
        <h1>Generated React App</h1>
        <p>PLACEHOLDER_PROMPT</p>
      </header>
      <main>
        <button onClick={() => alert('Hello from generated app')}>Click me</button>
      </main>
    </div>
  );
}
"""
        # Replace the placeholder with the user's prompt
        app_jsx = app_jsx.replace("PLACEHOLDER_PROMPT", user_prompt)

        # Files dictionary
        files = {
            "package.json": dedent("""{
  "name": "generated-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {"start": "vite", "build": "vite build"},
  "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
  "devDependencies": {"vite": "^4.5.0"}
}"""),
            "index.html": dedent("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Generated React App</title>
</head>
<body>
<div id="root"></div>
<script type="module" src="/src/main.jsx"></script>
</body>
</html>"""),
            "src/main.jsx": dedent("""import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles.css';
createRoot(document.getElementById('root')).render(<App />);"""),
            "src/App.jsx": app_jsx,
            "src/styles.css": dedent("""body { margin:0; font-family: Arial, sans-serif; } .app { max-width:960px; margin:24px auto; }"""),
        }

        # Static preview HTML for Streamlit
        files["index_preview.html"] = dedent(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Preview</title>
<style>
body {{ font-family: Arial, sans-serif; padding: 24px; max-width: 960px; margin: auto; }}
header {{ text-align: center; }}
button {{ padding: 8px 16px; }}
</style>
</head>
<body>
<header>
<h1>Generated React App Preview</h1>
<p>{user_prompt}</p>
</header>
<main>
<button onclick="alert('Hello from generated app')">Click me</button>
</main>
</body>
</html>""")
        return files

# ---------------------
# LLM Generator
# ---------------------
def llm_generate(user_prompt: str, framework: str, model: str, api_key: str):
    system_msg = {"role": "system", "content": "You are a frontend project generator. Output ONLY code blocks with file markers."}
    user_msg = {"role": "user", "content": dedent(f"""
        Generate a complete {framework} project.
        Format MUST be strictly:
        --- filename.ext ---
        (file contents)
        --- end ---
        Provide all files to run the project locally.
        User description:
        \"\"\"{user_prompt}\"\"\"
    """)}
    resp = completion(
        model=model,
        messages=[system_msg, user_msg],
        temperature=0.2,
        max_tokens=4000,
        api_key=api_key
    )
    text = resp["choices"][0]["message"]["content"]
    return safe_extract_code_blocks(text), text

# ---------------------
# Streamlit UI
# ---------------------
st.set_page_config(page_title="Frontend Generator (Advanced)", layout="wide")
st.title("🔧 Frontend Developer — Advanced (React / Tailwind / HTML)")

# Sidebar
with st.sidebar:
    st.header("Generation Settings")
    framework = st.selectbox("Framework", ["React + Tailwind", "Static HTML/CSS"])
    model = st.selectbox("Groq model (if using LLM)", DEFAULT_GROQ_MODELS)
    use_llm = st.checkbox("Use Groq LLM (requires valid API key)", value=False)
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    st.markdown("✅ API key detected" if GROQ_API_KEY else "⚠️ No API key found — using mock generator")
    st.markdown("---")
    st.write("Advanced options:")
    show_debug = st.checkbox("Show raw LLM output & debug", value=False)
    unique_folder = st.checkbox("Save each generation to a timestamped folder", value=True)

prompt = st.text_area("Describe the website you want:", height=160, value="A React + Tailwind dashboard with navbar, sidebar, dark mode, and pages for Home, Analytics and Settings")

col1, col2 = st.columns([2,1])
with col1:
    if st.button("Generate Project"):
        st.session_state.setdefault("last_action", {})
        st.session_state["last_action"] = {"prompt": prompt, "framework": framework, "model": model, "use_llm": use_llm}
        try:
            st.info("Generating...")
            if use_llm and GROQ_API_KEY and LITELLM_AVAILABLE:
                files_dict, raw_text = llm_generate(prompt, framework, model, GROQ_API_KEY)
                if show_debug:
                    st.subheader("Raw LLM output (first 4000 chars):")
                    st.text_area("LLM raw output", raw_text, height=300)
            else:
                files_dict = mock_generator(prompt, framework)

            if not files_dict:
                st.error("No files were generated.")
            else:
                project_folder = timestamped_folder(OUTPUT_ROOT, "generated_frontend") if unique_folder else OUTPUT_ROOT / "generated_frontend"
                if project_folder.exists():
                    shutil.rmtree(project_folder)
                project_folder.mkdir(parents=True, exist_ok=True)

                for fname, content in files_dict.items():
                    file_path = project_folder / fname
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding="utf-8")
                    st.write(f"Saved: `{file_path}`")

                zip_path = project_folder.with_suffix(".zip")
                make_zip_from_folder(project_folder, zip_path)

                st.success("Generation complete!")
                st.markdown(f"**Project folder:** `{project_folder}`")
                st.download_button("Download project ZIP", data=zip_path.read_bytes(), file_name=zip_path.name, mime="application/zip")

                st.subheader("Files generated")
                for f in sorted([p.relative_to(project_folder) for p in project_folder.rglob('*') if p.is_file()]):
                    st.code(str(f), language="")

                # Use preview HTML if React
                preview_file = project_folder / "index_preview.html" if (project_folder / "index_preview.html").exists() else project_folder / "index.html"
                if preview_file.exists():
                    st.subheader("Live preview")
                    html_content = preview_file.read_text(encoding="utf-8")
                    st.components.v1.html(html_content, height=600, scrolling=True, unsafe_allow_html=True)
                else:
                    st.info("No preview available.")
        except Exception as e:
            st.error(f"Error during generation: {e}")

with col2:
    st.header("Quick actions / Tips")
    st.markdown("""
    - Use specific prompts. Example:
      `React + Tailwind dashboard with navbar, sidebar, dark mode toggle, and pages Home/Analytics/Settings. Use React Router.`
    - To run a generated React project locally:
      1. `cd generated_project_folder`
      2. `npm install`
      3. `npm run dev`
    """)
    st.markdown("---")
    st.write("Debug / environment")
    st.write(f"litellm available: {LITELLM_AVAILABLE}")
    st.write(f"Groq API key present: {'yes' if GROQ_API_KEY else 'no'}")
    st.write(f"Output root: `{OUTPUT_ROOT.resolve()}`")

st.markdown("---")
st.caption("Generated projects are saved in the `output/` folder. Keep your API keys secure.")

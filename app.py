# streamlit_app.py
import os
import re
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from textwrap import dedent

import streamlit as st

# Try to import litellm lazily (only used if a real API key is present)
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except Exception:
    completion = None
    LITELLM_AVAILABLE = False

# ---------------------
# Configuration
# ---------------------
OUTPUT_ROOT = Path("output")
OUTPUT_ROOT.mkdir(exist_ok=True, parents=True)

# Default models to show (Groq-supported)
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
    folder.mkdir(parents=True, exist_ok=False)
    return folder

def make_zip_from_folder(folder: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in folder.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(folder))

def safe_extract_code_blocks(text: str):
    """
    Extract code blocks marked with:
      --- filename ---
      (code)
      --- end ---
    Returns dict filename -> content
    """
    pattern = r"---\s*(.*?)\s*---\n(.*?)---\s*end\s*---"
    matches = re.findall(pattern, text, re.DOTALL)
    files = {}
    if matches:
        for filename, content in matches:
            files[filename.strip()] = content.strip()
        return files

    # fallback: try to find triple-backtick blocks and assign names heuristically
    codeblocks = re.findall(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    if codeblocks:
        # assign numeric names if nothing else
        for i, cb in enumerate(codeblocks, 1):
            fname = f"file_{i}.txt"
            files[fname] = cb.strip()
        return files

    # fallback: if text looks like a single HTML page, return index.html
    if "<html" in text.lower() or "<!doctype html" in text.lower():
        return {"index.html": text.strip()}

    return {}

def mock_generator(user_prompt: str, framework: str):
    """
    Returns a dict of files for testing without LLM access.
    Uses framework param to return HTML or React starter.
    """
    if "react" in framework.lower():
        # small React + Tailwind starter (single-file components simplified)
        return {
            "package.json": dedent(
                """
                {
                  "name": "generated-frontend",
                  "version": "1.0.0",
                  "private": true,
                  "scripts": {
                    "start": "vite",
                    "build": "vite build"
                  },
                  "dependencies": {
                    "react": "^18.0.0",
                    "react-dom": "^18.0.0"
                  },
                  "devDependencies": {
                    "vite": "^4.0.0"
                  }
                }
                """
            ),
            "index.html": dedent(
                """<!doctype html>
                <html>
                  <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width,initial-scale=1.0">
                    <title>Generated React App</title>
                  </head>
                  <body>
                    <div id="root"></div>
                    <script type="module" src="/src/main.jsx"></script>
                  </body>
                </html>"""
            ),
            "src/main.jsx": dedent(
                """
                import React from 'react'
                import { createRoot } from 'react-dom/client'
                import App from './App.jsx'
                import './styles.css'

                createRoot(document.getElementById('root')).render(<App />)
                """
            ),
           "src/App.jsx": dedent(
             f"""
             import React from 'react'

           export default function App() {{
            return (
               <div className="app" style={{ padding: 24, fontFamily: 'Arial' }}>
               <header style={{ textAlign: 'center' }}>
               <h1>Generated React + Tailwind-like App</h1>
               <p>{user_prompt}</p>
              </header>
             <main>
               <button onClick={() => alert('Hello from generated app')}>Click me</button>
             </main>
               </div>
        )
        }}
     """
      ),

           
            "src/styles.css": dedent(
                """
                body { margin:0; font-family: Arial, sans-serif; }
                .app { max-width:960px; margin:24px auto; }
                """
            ),
        }
    else:
        # simple static HTML/CSS
        return {
            "index.html": dedent(
                f"""<!doctype html>
                <html>
                  <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width,initial-scale=1.0">
                    <title>Generated Page</title>
                    <link rel="stylesheet" href="styles.css">
                  </head>
                  <body>
                    <header><h1>Landing</h1></header>
                    <main>
                      <p>{user_prompt}</p>
                      <button onclick="alert('Hello!')">Click me</button>
                    </main>
                  </body>
                </html>
                """
            ),
            "styles.css": dedent(
                """
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                header { background: #f4f4f4; padding: 20px; text-align: center; }
                """
            ),
        }

# ---------------------
# LLM Generator (Groq via LiteLLM)
# ---------------------
def llm_generate(user_prompt: str, framework: str, model: str, api_key: str):
    """
    Calls the LLM (via litellm.completion) and returns dict filename->content.
    This function assumes completion is available and api_key is a valid Groq key.
    """
    system_msg = {"role": "system", "content": "You are a frontend project generator. Output ONLY code blocks with file markers."}
    user_msg = {"role": "user", "content": dedent(
        f"""
        Generate a complete {framework} project based on the description below.
        Format MUST be strictly (no extra explanation):

        --- filename.ext ---
        (file contents)
        --- end ---

        Provide all files necessary to run the project locally.
        User description:
        \"\"\"{user_prompt}\"\"\"
        """
    )}

    # call completion; pass api_key to ensure correct provider usage
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
st.title("🔧 Frontend Generator — Advanced (React / Tailwind / HTML)")

# Left column: inputs
with st.sidebar:
    st.header("Generation Settings")
    framework = st.selectbox("Framework", ["React + Tailwind", "Static HTML/CSS"])
    model = st.selectbox("Groq model (if using LLM)", DEFAULT_GROQ_MODELS)
    use_llm = st.checkbox("Use Groq LLM (requires valid API key)", value=False)

    # load key from Streamlit secrets or env
    GROQ_API_KEY = None
    if "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

    if GROQ_API_KEY:
        st.markdown("✅ API key detected")
    else:
        st.markdown("⚠️ No API key found — app will use mock generator if LLM is enabled")

    st.markdown("---")
    st.write("Advanced options:")
    show_debug = st.checkbox("Show raw LLM output & debug", value=False)
    unique_folder = st.checkbox("Save each generation to a timestamped folder", value=True)

prompt = st.text_area("Describe the website you want (be specific):", height=160, value="A React + Tailwind dashboard with navbar, sidebar, dark mode, and pages for Home, Analytics and Settings")

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Generate Project"):
        st.session_state.get("last_action", None)
        st.session_state["last_action"] = {"prompt": prompt, "framework": framework, "model": model, "use_llm": use_llm}
        # Run generation
        try:
            st.info("Generating... (this may take a few seconds)")
            if use_llm and GROQ_API_KEY and LITELLM_AVAILABLE:
                files_dict, raw_text = llm_generate(prompt, framework, model, GROQ_API_KEY)
                if show_debug:
                    st.subheader("Raw LLM output (first 4000 chars):")
                    st.text_area("LLM raw output", raw_text, height=300)
            elif use_llm and (not LITELLM_AVAILABLE or not GROQ_API_KEY):
                st.warning("LLM requested but not available (missing litellm or API key). Using mock generator instead.")
                files_dict = mock_generator(prompt, framework)
            else:
                # mock generator path
                files_dict = mock_generator(prompt, framework)

            if not files_dict:
                st.error("No files were generated. The LLM may have returned an unexpected format.")
            else:
                # create save folder
                if unique_folder:
                    project_folder = timestamped_folder(OUTPUT_ROOT, prefix="generated_frontend")
                else:
                    project_folder = OUTPUT_ROOT / "generated_frontend"
                    if project_folder.exists():
                        shutil.rmtree(project_folder)
                    project_folder.mkdir(parents=True, exist_ok=True)

                # write files
                for fname, content in files_dict.items():
                    file_path = project_folder / fname
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding="utf-8")
                    st.write(f"Saved: `{file_path}`")

                # create zip
                zip_path = project_folder.with_suffix(".zip")
                make_zip_from_folder(project_folder, zip_path)

                st.success("Generation complete!")
                st.markdown(f"**Project folder:** `{project_folder}`")
                st.download_button(
                    "Download project ZIP",
                    data=zip_path.read_bytes(),
                    file_name=zip_path.name,
                    mime="application/zip"
                )

                # show file list
                st.subheader("Files generated")
                for f in sorted([p.relative_to(project_folder) for p in project_folder.rglob('*') if p.is_file()]):
                    st.code(str(f), language="")

                # show preview if index.html present
                if (project_folder / "index.html").exists():
                    st.subheader("Live preview (index.html)")
                    html_content = (project_folder / "index.html").read_text(encoding="utf-8")
                    st.components.v1.html(html_content, height=600, scrolling=True)
                else:
                    st.info("No index.html to preview. Open the downloaded project locally to view it.")

        except Exception as e:
            st.error(f"Error during generation: {e}")

with col2:
    st.header("Quick actions / Tips")
    st.markdown(
        """
        - Use specific prompts. Example:
          `React + Tailwind dashboard with navbar, sidebar, dark mode toggle, and pages Home/Analytics/Settings. Use React Router.`
        - If the LLM output is malformed, enable 'Show raw LLM output' and copy the block markers format into your prompt to enforce structure.
        - To run a generated React project locally:
          1. `cd generated_project_folder`
          2. `npm install`
          3. `npm run dev` (or `npm run build` then serve)
        """
    )
    st.markdown("---")
    st.write("Debug / environment")
    st.write(f"litellm available: {LITELLM_AVAILABLE}")
    st.write(f"Groq API key present: {'yes' if GROQ_API_KEY else 'no'}")
    st.write(f"Output root: `{OUTPUT_ROOT.resolve()}`")

st.markdown("---")
st.caption("Generated projects are saved in the `output/` folder. Keep your API keys secure: use Streamlit secrets when deploying.")

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


# ------------------------------------------------
# Helper functions
# ------------------------------------------------
def sanitize_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", filename)


def save_uploaded_file(uploaded_file, save_dir):
    save_path = Path(save_dir) / sanitize_filename(uploaded_file.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return save_path


def mock_generate_frontend_code(answers: dict) -> dict:
    """Fake generator for demo if no API key"""
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{answers.get('title','My Website')}</title>
        <style>
            body {{ font-family: Arial; }}
            header {{ background: #5B2E0F; color: white; padding: 1rem; }}
            footer {{ background: #eee; padding: 1rem; }}
        </style>
    </head>
    <body>
        <header><h1>{answers.get('title','My Website')}</h1></header>
        <main><p>{answers.get('description','A nice site.')}</p></main>
        {"<footer>Contact us at test@example.com</footer>" if answers.get("footer") else ""}
    </body>
    </html>
    """
    return {
        "html": html_code,
        "css": "body { margin:0; padding:0; }",
        "js": "console.log('Site loaded');"
    }


def generate_frontend_code(answers: dict) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not LITELLM_AVAILABLE:
        return mock_generate_frontend_code(answers)

    # Example Groq call
    prompt = dedent(f"""
    Generate frontend code (HTML, CSS, JS).
    Requirements: {answers}
    Return ONLY JSON with keys: html, css, js.
    """)
    response = completion(
        model="llama3-8b-8192",
        api_key=api_key,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.4,
    )
    try:
        return eval(response["choices"][0]["message"]["content"])
    except Exception:
        return mock_generate_frontend_code(answers)


# ------------------------------------------------
# Streamlit UI
# ------------------------------------------------
st.set_page_config(page_title="AI Website Builder", layout="wide")

if "qa_step" not in st.session_state:
    st.session_state.qa_step = 0
    st.session_state.qa_answers = {}
    st.session_state.qa_advanced = False
    st.session_state.generate_trigger = None


def go_next():
    st.session_state.qa_step += 1


def go_back():
    st.session_state.qa_step -= 1


step = st.session_state.qa_step
answers = st.session_state.qa_answers

st.sidebar.title("AI Website Builder")
st.sidebar.write("Answer questions to build your site.")

# -------------------------------
# Basic questions
# -------------------------------
if step == 0:
    title = st.text_input("1) Website title", value=answers.get("title", "My Website"))
    st.session_state.qa_answers["title"] = title
    if st.button("Next"): go_next()

elif step == 1:
    desc = st.text_area("2) Website description", value=answers.get("description", ""))
    st.session_state.qa_answers["description"] = desc
    if st.button("Next"): go_next()
    if st.button("Back"): go_back()

elif step == 2:
    contact_yes = st.radio("3) Include contact page?", ["Yes", "No"],
                           index=0 if answers.get("contact","No")=="Yes" else 1)
    st.session_state.qa_answers["contact"] = contact_yes
    if st.button("Next"): go_next()
    if st.button("Back"): go_back()

elif step == 3:
    about_yes = st.radio("4) Include about us page?", ["Yes", "No"],
                         index=0 if answers.get("about","No")=="Yes" else 1)
    st.session_state.qa_answers["about"] = about_yes
    if st.button("Next"): go_next()
    if st.button("Back"): go_back()

elif step == 4:
    navbar_yes = st.radio("5) Include navbar?", ["Yes", "No"],
                          index=0 if answers.get("navbar","Yes")=="Yes" else 1)
    st.session_state.qa_answers["navbar"] = navbar_yes
    if st.button("Next"): go_next()
    if st.button("Back"): go_back()

elif step == 5:
    adv = st.radio("Do you want advanced options?", ["Yes", "No"],
                   index=0 if st.session_state.qa_advanced else 1)
    st.session_state.qa_advanced = (adv == "Yes")
    if st.button("Next"): go_next()
    if st.button("Back"): go_back()

# -------------------------------
# Advanced questions (multi-step)
# -------------------------------
elif step == 6 and st.session_state.qa_advanced:
    footer_yes = st.radio("7) Footer?", ["Yes", "No"],
                          index=0 if answers.get("footer","No")=="Yes" else 1)
    st.session_state.qa_answers["footer"] = (footer_yes == "Yes")
    if st.button("Next"): go_next()
    if st.button("Back"): go_back()

elif step == 7 and st.session_state.qa_advanced:
    login_yes = st.radio("8) Login/signup page?", ["No", "Yes"],
                         index=0 if not answers.get("login",False) else 1)
    st.session_state.qa_answers["login"] = (login_yes == "Yes")
    if st.button("Next"): go_next()
    if st.button("Back"): go_back()

elif step == 8 and st.session_state.qa_advanced:
    charts_yes = st.radio("9) Include charts/cards?", ["No", "Yes"],
                          index=0 if not answers.get("charts",False) else 1)
    st.session_state.qa_answers["charts"] = (charts_yes == "Yes")
    if st.button("Next"): go_next()
    if st.button("Back"): go_back()

elif step == 9 and st.session_state.qa_advanced:
    theme_choice = st.selectbox("10) Theme", ["light", "dark", "custom"],
                                index=0 if answers.get("theme","light")=="light"
                                else (1 if answers.get("theme")=="dark" else 2))
    st.session_state.qa_answers["theme"] = theme_choice
    if theme_choice == "custom":
        col = st.text_input("Custom primary color (hex)",
                            value=answers.get("custom_color", "#5B2E0F"))
        st.session_state.qa_answers["custom_color"] = col
    if st.button("Next"): go_next()
    if st.button("Back"): go_back()

# -------------------------------
# Final review
# -------------------------------
elif (step == 6 and not st.session_state.qa_advanced) or (step == 10 and st.session_state.qa_advanced):
    st.write("You're ready to generate the website. Review your choices below:")
    st.json(st.session_state.qa_answers)
    if st.button("Generate site now"):
        st.session_state.generate_trigger = datetime.now().timestamp()
    if st.button("Back"): go_back()


# -------------------------------
# Preview output
# -------------------------------
if st.session_state.generate_trigger:
    st.subheader("Generated Website Preview")
    code_bundle = generate_frontend_code(st.session_state.qa_answers)

    tab1, tab2, tab3 = st.tabs(["HTML", "CSS", "JS"])
    with tab1: st.code(code_bundle["html"], language="html")
    with tab2: st.code(code_bundle["css"], language="css")
    with tab3: st.code(code_bundle["js"], language="javascript")

    if st.button("Download ZIP"):
        out_dir = Path("output")
        if out_dir.exists(): shutil.rmtree(out_dir)
        out_dir.mkdir()
        for fname, content in code_bundle.items():
            ext = fname if fname != "html" else "index.html"
            (out_dir / ext).write_text(content, encoding="utf-8")
        zip_path = "generated_frontend.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for file in out_dir.iterdir():
                zf.write(file, arcname=file.name)
        with open(zip_path, "rb") as f:
            st.download_button("Download Your Site", f, file_name=zip_path)

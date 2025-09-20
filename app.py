import os
import re
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from textwrap import dedent
import json

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
# Mock generator (creates a real React + Tailwind project or static HTML)
# ---------------------
def mock_generator_from_settings(settings: dict, framework: str):
    """
    settings: dict containing
      - title: str
      - navbar: bool
      - navbar_color: str (like 'bg-brown-700' or hex)
      - sidebar: bool
      - pages: list of page names (strings)
      - advanced: bool
      - footer: bool
      - login: bool
      - charts: bool
      - theme: 'light'|'dark'|'custom'
      - custom_color: str
    framework: "React + Tailwind" or "Static HTML/CSS"
    """
    title = settings.get("title", "My Site")
    navbar = settings.get("navbar", True)
    navbar_color = settings.get("navbar_color", "#5B2E0F")
    sidebar = settings.get("sidebar", True)
    pages = settings.get("pages", ["Home"])
    footer = settings.get("footer", False)
    login = settings.get("login", False)
    charts = settings.get("charts", False)
    theme = settings.get("theme", "light")
    custom_color = settings.get("custom_color", "#5B2E0F")
    about = settings.get("about", False)
    contact = settings.get("contact", False)


    files = {}

    if "react" in framework.lower():
        # package.json (include both start and dev for convenience)
        package_json = {
            "name": "generated-frontend",
            "version": "1.0.0",
            "private": True,
            "scripts": {
                "start": "vite",
                "dev": "vite",
                "build": "vite build"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.14.1"
            },
            "devDependencies": {
                "vite": "^4.5.0",
                "tailwindcss": "^3.5.0",
                "postcss": "^8.4.0",
                "autoprefixer": "^10.4.0"
            }
        }
        files["package.json"] = json.dumps(package_json, indent=2)

        # Vite index.html (entry)
        files["index.html"] = dedent("""<!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>Generated React App</title>
        </head>
        <body>
          <div id="root"></div>
          <script type="module" src="/src/main.jsx"></script>
        </body>
        </html>""")

        # tailwind config (simple)
        files["tailwind.config.cjs"] = dedent("""module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
}""")

        files["postcss.config.cjs"] = dedent("""module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  }
}""")

        # src/index.css (Tailwind directives)
        files["src/index.css"] = dedent("""@tailwind base;
@tailwind components;
@tailwind utilities;

/* custom global styles */
body { @apply bg-white text-gray-900; }
.dark body { @apply bg-gray-900 text-gray-100; }""")

        # src/main.jsx
        files["src/main.jsx"] = dedent("""import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter as Router } from 'react-router-dom';
import App from './App.jsx';
import './index.css';
createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Router>
      <App />
    </Router>
  </React.StrictMode>
);""")

        # Build App.jsx using placeholders and plain string (no f-strings)
        app_template = """
import React, { useState } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
PLACEHOLDER_IMPORTS

export default function App() {
  const [dark, setDark] = useState(false);
  return (
    <div className={dark ? 'dark' : ''}>
      <div className="min-h-screen flex">
        PLACEHOLDER_SIDEBAR
        <div className="flex-1 flex flex-col">
          PLACEHOLDER_NAV
          <main className="p-6 flex-1">
            <Routes>
              PLACEHOLDER_ROUTES
            </Routes>
          </main>
          PLACEHOLDER_FOOTER
        </div>
      </div>
    </div>
  );
}
"""
        # Create imports, sidebar, nav, routes, footer based on settings
        imports = ""
        sidebar_code = ""
        nav_code = ""
        routes_code = ""
        footer_code = ""

        # Pages components content
        page_files = {}
        for p in pages:
            comp_name = ''.join(word.capitalize() for word in p.split())
            page_js = f"""
import React from 'react';
export default function {comp_name}() {{
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">{p}</h2>
      <p>This is the {p} page generated by the Website Builder Agent.</p>
      PLACEHOLDER_EXTRA
    </div>
  );
}}
"""
            extra = ""
            
            if charts and p.lower() in ("analytics", "dashboard", "home"):
                extra = "<div className='mt-4 p-4 border rounded'>[Chart placeholder — replace with real chart]</div>"
            page_js = page_js.replace("PLACEHOLDER_EXTRA", extra)
            page_files[f"src/pages/{comp_name}.jsx"] = dedent(page_js)

            # import line for the page in App
            imports += f"import {comp_name} from './pages/{comp_name}.jsx';\n"

            # route entry
            route_path = "/" if p.lower() == "home" else "/" + p.lower().replace(" ", "-")
            route_code = '<Route path="' + route_path + '" element={' + '<' + comp_name + ' />' + '} />\n'
            routes_code += route_code

        # Track already-added pages
        # ------------------------------
        pages_added = set(pages)  # start with whatever user gave

        # ------------------------------
        # Extra pages: About, Contact, Login
        # ------------------------------
        if settings.get("about") and "About" not in pages_added:
            imports += "import About from './pages/About.jsx';\n"
            routes_code += '<Route path="/about" element={<About />} />\n'
            page_files["src/pages/About.jsx"] = dedent("""\
            import React from 'react';
            export default function About() {
              return (
                <div>
                  <h2 className="text-2xl font-semibold mb-4">About Us</h2>
                  <p>Welcome to our website! This is the about page.</p>
                </div>
              );
            }
            """)
            pages_added.add("About")

        if settings.get("contact") and "Contact" not in pages_added:
          imports += "import Contact from './pages/Contact.jsx';\n"
          routes_code += '<Route path="/contact" element={<Contact />} />\n'
          page_files["src/pages/Contact.jsx"] = dedent("""\
    import React, { useState } from 'react';

    export default function Contact() {
      const [form, setForm] = useState({ name: "", email: "", message: "" });

      const handleChange = (e) => {
        setForm({ ...form, [e.target.name]: e.target.value });
      };

      const handleSubmit = (e) => {
        e.preventDefault();
        alert(`Message sent!\\nName: ${form.name}\\nEmail: ${form.email}\\nMessage: ${form.message}`);
        setForm({ name: "", email: "", message: "" }); // reset
      };

      return (
        <div className="flex flex-col items-center p-6">
          <h2 className="text-2xl font-semibold mb-6">Contact Us</h2>
          <form
            onSubmit={handleSubmit}
            className="flex flex-col space-y-4 w-full max-w-md bg-white p-6 rounded-2xl shadow-lg"
          >
            <div>
              <label className="block text-gray-700 mb-2">Your Name</label>
              <input
                type="text"
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder="John Doe"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-gray-700 mb-2">Your Email</label>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-gray-700 mb-2">Message</label>
              <textarea
                name="message"
                value={form.message}
                onChange={handleChange}
                placeholder="Write your message..."
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows="4"
                required
              />
            </div>
            <button
              type="submit"
              className="bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition"
            >
              Send
            </button>
          </form>
        </div>
      );
    }
    """)
          pages_added.add("Contact")

           

        if login and "Login" not in pages_added:
          imports += "import Login from './pages/Login.jsx';\n"
          routes_code += '<Route path="/login" element={<Login />} />\n'
          page_files["src/pages/Login.jsx"] = dedent("""\
    import React from 'react';

    export default function Login() {
      return (
        <div className="flex flex-col items-center p-6">
          <h2 className="text-2xl font-semibold mb-6">Login</h2>
          <form className="w-full max-w-sm bg-white p-6 rounded-2xl shadow-lg space-y-4">
            <div>
              <label className="block text-gray-700 mb-2">Email</label>
              <input
                type="email"
                placeholder="you@example.com"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <div>
              <label className="block text-gray-700 mb-2">Password</label>
              <input
                type="password"
                placeholder="Enter your password"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <button
              type="submit"
              className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition"
            >
              Login
            </button>
          </form>
        </div>
      );
    }
    """)
          pages_added.add("Login")


           

        # Sidebar
        if sidebar:
            sidebar_code = dedent(f"""
            <aside className="w-64 bg-gray-100 dark:bg-gray-800 p-4 hidden md:block">
              <div className="text-xl font-bold mb-6">{title}</div>
              <nav>
                {"".join([f'<div className="mb-2"><Link to="{"/" if p.lower()=="home" else "/" + p.lower()}" className="block py-2 px-3 rounded hover:bg-gray-200 dark:hover:bg-gray-700">{p}</Link></div>' for p in pages])}
              </nav>
            </aside>
            """)
        else:
            sidebar_code = ""  # no sidebar, content occupies full width

        # Navbar
        if navbar:
            # If navbar_color is hex, apply inline style; else allow Tailwind class
            if navbar_color.startswith("#"):
                nav_style = f"style={{background: '{navbar_color}'}}"
                nav_elem = dedent(f"""
                <header className="flex items-center justify-between p-4" {nav_style}>
                  <div className="flex items-center space-x-3">
                    <div className="text-lg font-bold">{title}</div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <button onClick={{() => setDark(!dark)}} className="px-3 py-1 rounded bg-white text-black">Toggle theme</button>
                  </div>
                </header>
                """)
            else:
                nav_elem = dedent(f"""
                <header className="flex items-center justify-between p-4 {navbar_color} text-white">
                  <div className="flex items-center space-x-3">
                    <div className="text-lg font-bold">{title}</div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <button onClick={{() => setDark(!dark)}} className="px-3 py-1 rounded bg-white text-black">Toggle theme</button>
                  </div>
                </header>
                """)
            nav_code = nav_elem
        else:
            nav_code = ""

        # Footer
        if footer:
            footer_code = dedent(f"""
            <footer className="p-4 bg-gray-100 dark:bg-gray-900 text-sm text-center">
              © {datetime.now().year} {title} — Generated by Website Builder Agent
            </footer>
            """)
        else:
            footer_code = ""

        # Compose final App.jsx by replacing placeholders
        final_app = app_template
        final_app = final_app.replace("PLACEHOLDER_IMPORTS", imports)
        final_app = final_app.replace("PLACEHOLDER_SIDEBAR", sidebar_code)
        final_app = final_app.replace("PLACEHOLDER_NAV", nav_code)
        final_app = final_app.replace("PLACEHOLDER_ROUTES", routes_code)
        final_app = final_app.replace("PLACEHOLDER_FOOTER", footer_code)

        files["src/App.jsx"] = dedent(final_app)

        # Add page files
        for path, content in page_files.items():
            files[path] = content

        # styles.css fallback (small)
        files["src/styles.css"] = dedent("""/* Basic styles in case Tailwind not initialized yet */
body { margin: 0; font-family: Arial, Helvetica, sans-serif; } .app { max-width: 1200px; margin: 0 auto; }""")

        # Add README and setup scripts
        files["README.md"] = dedent(f"# {title}\n\nGenerated by Website Builder Agent.\n\nRun `npm install` then `npm start` to view locally.")
        files["setup.sh"] = dedent("""#!/usr/bin/env bash
npm install
npm run dev
""")
        files["setup.bat"] = dedent("""@echo off
npm install
npm start
pause
""")

        # Static preview HTML for Streamlit: simple, reflects choices
        preview_html = dedent(f"""<!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>Preview - {title}</title>
          <style>
            body {{ font-family: Arial, Helvetica, sans-serif; padding: 24px; max-width: 1100px; margin:auto; }}
            header {{ background:{navbar_color}; color: white; padding: 12px 18px; border-radius:6px; }}
            aside {{ width:220px; float:left; margin-right:18px; background:#f2f2f2; padding:12px; border-radius:6px; }}
            main {{ overflow:auto; }}
            .card {{ padding:12px; border:1px solid #e6e6e6; border-radius:6px; margin-bottom:12px; }}
          </style>
        </head>
        <body>
          <header><h1>{title}</h1></header>
          <div style="display:flex; gap:18px; margin-top:18px;">
            {"<aside><nav>" + "".join([f"<div><a href='#'>{p}</a></div>" for p in pages]) + "</nav></aside>" if sidebar else ""}
            <main style="flex:1;">
              <div class="card"><h2>{pages[0]}</h2><p>Example content for {pages[0]} page.</p></div>
              {"<div class='card'><h3>Charts</h3><p>Placeholder chart area</p></div>" if charts else ""}
              {"<div class='card'><h3>Login</h3><p>Login page included</p></div>" if login else ""}
            </main>
          </div>
        </body>
        </html>""")
        files["index_preview.html"] = preview_html

        return files

    else:
        # Static HTML/CSS generator for simple sites
        pages = settings.get("pages", ["Home"])
        title = settings.get("title", "My Site")
        body_html = ""
        for p in pages:
            body_html += f"<section><h2>{p}</h2><p>Auto generated {p} page.</p></section>\n"
        index_html = dedent(f"""<!doctype html>
        <html>
        <head>
          <meta charset="utf-8"/>
          <meta name="viewport" content="width=device-width,initial-scale=1">
          <title>{title}</title>
          <style>body{{font-family:Arial; padding:20px;}} header{{background:#222;color:#fff;padding:12px;border-radius:6px}}</style>
        </head>
        <body>
          <header><h1>{title}</h1></header>
          {body_html}
        </body>
        </html>""")
        files["index.html"] = index_html
        files["styles.css"] = "/* simple */"
        return files

# ---------------------
# LLM Generator wrapper (keeps previous behaviour but now uses a composed prompt)
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
# Streamlit UI + Q&A flow
# ---------------------
st.set_page_config(page_title="Website Builder Agent", layout="wide")
st.title("⚙️ Website Builder Agent — Chat to generate sites")

# Sidebar Q&A flow controls
if "qa_step" not in st.session_state:
    st.session_state.qa_step = 0
if "qa_answers" not in st.session_state:
    st.session_state.qa_answers = {}
if "qa_advanced" not in st.session_state:
    st.session_state.qa_advanced = False

with st.sidebar:
    st.header("Agent conversation")
    st.write("Answer a few questions and the agent will generate a website for you.")
    # Define the question flow
    step = st.session_state.qa_step
    answers = st.session_state.qa_answers

    def go_next():
        st.session_state.qa_step += 1

    def go_back():
        if st.session_state.qa_step > 0:
            st.session_state.qa_step -= 1

    # Step 0: Title
    if step == 0:
        title_in = st.text_input("1) Website name/title", value=answers.get("title", "My Site"))
        st.session_state.qa_answers["title"] = title_in
        if st.button("Next"):
            go_next()

    # Step 1: Framework
    elif step == 1:
        framework_choice = st.selectbox("2) Framework", ["React + Tailwind", "Static HTML/CSS"], index=0 if answers.get("framework","React + Tailwind")=="React + Tailwind" else 1)
        st.session_state.qa_answers["framework"] = framework_choice
        if st.button("Next"):
            go_next()
        if st.button("Back"):
            go_back()

    # Step 2: Navbar
    elif step == 2:
        nav_yes = st.radio("3) Navbar?", ["Yes", "No"], index=0 if answers.get("navbar","Yes")=="Yes" else 1)
        st.session_state.qa_answers["navbar"] = (nav_yes == "Yes")
        if st.session_state.qa_answers["navbar"]:
            color = st.text_input("Navbar color (hex like #5B2E0F or tailwind class e.g. bg-brown-700)", value=answers.get("navbar_color", "#5B2E0F"))
            st.session_state.qa_answers["navbar_color"] = color
        if st.button("Next"):
            go_next()
        if st.button("Back"):
            go_back()

    # Step 3: Sidebar
    elif step == 3:
        sidebar_yes = st.radio("4) Sidebar?", ["Yes", "No"], index=0 if answers.get("sidebar","Yes")=="Yes" else 1)
        st.session_state.qa_answers["sidebar"] = (sidebar_yes == "Yes")
        if st.button("Next"):
            go_next()
        if st.button("Back"):
            go_back()

    # Step 4: Pages
    elif step == 4:
        pages_text = st.text_input("5) Pages (comma separated). Example: Home, Analytics, Settings", value=", ".join(answers.get("pages", ["Home", "Analytics", "Settings"])))
        pages_list = [p.strip() for p in pages_text.split(",") if p.strip()]
        if not pages_list:
            st.warning("Please provide at least one page name.")
        else:
            st.session_state.qa_answers["pages"] = pages_list
        if st.button("Next"):
            go_next()
        if st.button("Back"):
            go_back()

    # Step 5: Advanced or not
    elif step == 5:
        adv = st.radio("6) Do you want to customize more features? (footer, login, charts, dark mode)", ["No", "Yes"], index=0 if not st.session_state.qa_advanced else 1)
        st.session_state.qa_advanced = (adv == "Yes")

        if adv == "Yes":
            st.write("You selected to customize more features.")
            if st.button("Continue"):
                go_next()   # go to advanced step 6
        else:
            st.write("Agent will generate a basic site based on previous answers.")
            if st.button("Finish"):
                st.session_state.qa_step = 6   # jump directly to final confirmation

        if st.button("Back"):
            go_back()

    # Advanced questions (only if chosen)
    elif step == 6 and st.session_state.qa_advanced:
        footer_yes = st.radio("7) Footer?", ["Yes", "No"], index=0 if answers.get("footer","No")=="Yes" else 1)
        st.session_state.qa_answers["footer"] = (footer_yes == "Yes")

        login_yes = st.radio("8) Login/signup page?", ["No", "Yes"], index=0 if not answers.get("login",False) else 1)
        st.session_state.qa_answers["login"] = (login_yes == "Yes")

        charts_yes = st.radio("9) Include charts/cards in pages like Analytics?", ["No", "Yes"], index=0 if not answers.get("charts",False) else 1)
        st.session_state.qa_answers["charts"] = (charts_yes == "Yes")

        theme_choice = st.selectbox("10) Theme", ["light", "dark", "custom"],
                                    index=0 if answers.get("theme","light")=="light"
                                    else (1 if answers.get("theme")=="dark" else 2))
        st.session_state.qa_answers["theme"] = theme_choice

        if theme_choice == "custom":
            col = st.text_input("Custom primary color (hex)", value=answers.get("custom_color", "#5B2E0F"))
            st.session_state.qa_answers["custom_color"] = col

        # ✅ New advanced questions
        contact_yes = st.radio("11) Contact page?", ["No", "Yes"], index=0 if not answers.get("contact", False) else 1)
        st.session_state.qa_answers["contact"] = (contact_yes == "Yes")

        about_yes = st.radio("12) About Us page?", ["No", "Yes"], index=0 if not answers.get("about", False) else 1)
        st.session_state.qa_answers["about"] = (about_yes == "Yes")

        if st.button("Next"):
            go_next()
        if st.button("Back"):
            go_back()

    # Final step: confirm and generate
    elif (step == 6 and not st.session_state.qa_advanced) or (step == 7 and st.session_state.qa_advanced):
        st.write("You're ready to generate the website. Review your choices below:")

        # ✅ Nicely formatted summary
        st.markdown(f"""
        - **Footer:** {'Yes' if st.session_state.qa_answers.get('footer') else 'No'}
        - **Login/Signup Page:** {'Yes' if st.session_state.qa_answers.get('login') else 'No'}
        - **Charts/Analytics:** {'Yes' if st.session_state.qa_answers.get('charts') else 'No'}
        - **Theme:** {st.session_state.qa_answers.get('theme', 'light')}
        - **Custom Color:** {st.session_state.qa_answers.get('custom_color', 'N/A')}
        - **Contact Page:** {'Yes' if st.session_state.qa_answers.get('contact') else 'No'}
        - **About Us Page:** {'Yes' if st.session_state.qa_answers.get('about') else 'No'}
        """)

        # Still keep full JSON for debugging
        st.json(st.session_state.qa_answers)

        if st.button("Generate site now"):
            # Move to main area trigger
            st.session_state.generate_trigger = datetime.now().timestamp()
        if st.button("Back"):
            go_back()

# Main area: show conversation summary and handle generation
col1, col2 = st.columns([2, 1])
with col1:
    st.header("Conversation preview")
    st.write("The agent will ask questions in the sidebar. When finished, click 'Generate site now'.")
    st.write("Current answers:")
    st.write(st.session_state.qa_answers)

    # If generation triggered, build settings and call generator
    # Collect inputs from user (always visible in sidebar or main app)
    st.session_state.qa_answers["contact"] = st.checkbox("Include Contact Page?", value=False)
    st.session_state.qa_answers["about"] = st.checkbox("Include About Page?", value=False)
    st.session_state.qa_answers["login"] = st.checkbox("Include Login Page?", value=False)
    pages = st.session_state.qa_answers.get("pages", [])
    if not pages:
       pages = ["Home"]
    st.session_state.qa_answers["pages"] = pages
    if st.session_state.get("generate_trigger"):
        st.info("Building site from your answers...")
        settings = {
            "title": st.session_state.qa_answers.get("title", "My Site"),
            "navbar": st.session_state.qa_answers.get("navbar", True),
            "navbar_color": st.session_state.qa_answers.get("navbar_color", "#5B2E0F"),
            "sidebar": st.session_state.qa_answers.get("sidebar", True),
            "pages": pages,
            "footer": st.session_state.qa_answers.get("footer", False),
            "login": st.session_state.qa_answers.get("login", False),
            "charts": st.session_state.qa_answers.get("charts", False),
            "theme": st.session_state.qa_answers.get("theme", "light"),
            "custom_color": st.session_state.qa_answers.get("custom_color", "#5B2E0F"),
            "contact": st.session_state.qa_answers.get("contact", False),
            "about": st.session_state.qa_answers.get("about", False),
        }
        if settings["contact"] and "Contact" not in settings["pages"]:
           settings["pages"].append("Contact")
        if settings["login"] and "Login" not in settings["pages"]:
           settings["pages"].append("Login")
        if settings["about"] and "About" not in settings["pages"]:
           settings["pages"].append("About")
        framework = st.session_state.qa_answers.get("framework", "React + Tailwind")

        try:
            # Use LLM if requested and available, else mock generator
            if st.session_state.qa_answers.get("framework") and st.session_state.qa_answers.get("framework").lower().startswith("react") and st.sidebar.checkbox("Use Groq LLM (generate with model)", value=False):
                # If user wants to use the LLM, compose a single prompt
                combined_prompt = f"""Create a complete {framework} project with the following settings:
Title: {settings['title']}
Navbar: {settings['navbar']} (color: {settings['navbar_color']})
Sidebar: {settings['sidebar']}
Pages: {', '.join(settings['pages'])}
Footer: {settings['footer']}
Login page: {settings['login']}
Charts: {settings['charts']}
Theme: {settings['theme']}
Custom color: {settings['custom_color']}
Provide all files with markers like --- filename --- (file contents) --- end ---.
"""
                GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
                model = st.sidebar.selectbox("Groq model", DEFAULT_GROQ_MODELS)
                if not GROQ_API_KEY:
                    st.warning("No API key found — falling back to local mock generator.")
                    files_dict = mock_generator_from_settings(settings, framework)
                else:
                    files_dict, raw_text = llm_generate(combined_prompt, framework, model, GROQ_API_KEY)
            else:
                files_dict = mock_generator_from_settings(settings, framework)

            if not files_dict:
                st.error("No files were generated.")
            else:
                project_folder = timestamped_folder(OUTPUT_ROOT, "generated_frontend")
                if project_folder.exists():
                    shutil.rmtree(project_folder)
                project_folder.mkdir(parents=True, exist_ok=True)

                for fname, content in files_dict.items():
                    file_path = project_folder / fname
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    # If content is not string (like bytes), convert to str
                    if isinstance(content, bytes):
                        file_path.write_bytes(content)
                    else:
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

                preview_file = project_folder / "index_preview.html" if (project_folder / "index_preview.html").exists() else project_folder / "index.html"
                if preview_file.exists():
                    st.subheader("Live preview")
                    html_content = preview_file.read_text(encoding="utf-8")
                    st.components.v1.html(html_content, height=600, scrolling=True)
                else:
                    st.info("No preview available.")

        except Exception as e:
            st.error(f"Error during generation: {e}")

with col2:
    st.header("Quick actions / Tips")
    st.markdown("""
    - Use the sidebar to answer questions step-by-step.
    - After generation, download the ZIP and run locally:
      1. `cd generated_project_folder`
      2. `npm install`
      3. `npm start` (or `npm run dev`)
    - Or double-click `setup.bat` (Windows) or run `./setup.sh` (Unix) to auto-install and start.
    """)
    st.markdown("---")
    st.write("Debug / environment")
    st.write(f"litellm available: {LITELLM_AVAILABLE}")
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    st.write(f"Groq API key present: {'yes' if GROQ_API_KEY else 'no'}")
    st.write(f"Output root: `{OUTPUT_ROOT.resolve()}`")

st.markdown("---")
st.caption("Generated projects are saved in the `output/` folder. Keep your API keys secure.")

import streamlit as st
from pathlib import Path
import zipfile
from generator import generate_project_from_prompt  # your mock or real generator

# Ensure output folder exists
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="Frontend Generator Agent", layout="wide")
st.title("Frontend Generator Agent")

# User input
user_prompt = st.text_area(
    "Describe the website you want (e.g., React + Tailwind portfolio with hero, projects, contact form):"
)

# Button to generate website
if st.button("Generate & Download ZIP"):
    if not user_prompt.strip():
        st.warning("Please enter a prompt describing the website.")
    else:
        try:
            # Generate project files
            project_files = generate_project_from_prompt(user_prompt)

            # Save files permanently
            project_folder = OUTPUT_DIR / "generated_frontend"
            project_folder.mkdir(exist_ok=True, parents=True)

            for filename, content in project_files.items():
                file_path = project_folder / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
                st.text(f"Saved file: {file_path}")

            # Create ZIP
            zip_path = OUTPUT_DIR / "generated_frontend.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in project_folder.rglob("*"):
                    if file.is_file():
                        zf.write(file, arcname=file.relative_to(project_folder))

            st.success("Website generated successfully!")
            st.download_button(
                label="Download ZIP",
                data=zip_path.read_bytes(),
                file_name="generated_frontend.zip",
                mime="application/zip",
            )

        except Exception as e:
            st.error(f"Error generating website: {e}")

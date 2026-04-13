import os
import subprocess
from google import genai

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    project_id = os.getenv("PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")

    if api_key:
        print("🚀 Using Google AI Studio API Key...")
        return genai.Client(api_key=api_key)

    print("🛡️ Using Vertex AI Service Account...")
    return genai.Client(
        vertexai=True,
        project=project_id,
        location="global",
    )


def get_git_history():
    try:
        cmd = ["git", "log", "-n", "8", "--pretty=format:%h | %ad | %s", "--date=short"]
        return subprocess.check_output(cmd).decode("utf-8")
    except Exception:
        return "Initial release."


def get_repo_context():
    files = ["app.py", "cloudbuild.yaml", "Dockerfile", "requirements.txt"]
    context = ""
    for f_name in files:
        if os.path.exists(f_name):
            with open(f_name, "r", encoding="utf-8", errors="replace") as f:
                context += f"\n--- {f_name} ---\n{f.read()}\n"
    return context[:18000]


def write_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def generate_markdown(client, task: str, context: str) -> str:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"""
You are writing enterprise-style technical documentation for a Google Cloud proof-of-concept project.

Repository context:
{context}

Task:
{task}

Global writing rules:
- Output Markdown only
- Use a formal technical documentation tone
- Do not write like a chatbot
- Do not use casual wording
- Prefer numbered sections and subsections
- Be specific to the repository context
- Do not invent services, modules, files, or deployment steps not supported by the context
- Prefer precise implementation details over generic statements
- Use clean headings, short paragraphs, and bullet points only when necessary
- Where diagrams are requested, output valid Mermaid fenced code blocks only
- Never output Mermaid syntax as plain paragraph text
- Do not wrap the whole response in triple backticks
""".strip()
    )

    return response.text or ""


def generate_docs():
    client = get_client()
    context = get_repo_context()
    history = get_git_history()

    os.makedirs("docs", exist_ok=True)

    sections = {
        "index.md": """
Create the main project documentation page for GES-POC.

Required title:
# GES Audio Processing POC - Technical Documentation

Required sections:
1. Executive Summary
2. Business Objective
3. Scope of the POC
4. Key Capabilities
5. Technology Stack
6. Project Structure Overview
7. Operational Flow Summary

Content expectations:
- Explain the purpose of the project in enterprise documentation style
- Describe how audio is uploaded, processed, masked, stored, and reported
- Mention only components supported by the repository context
- Keep this page suitable as the main landing page of an MkDocs site
""".strip(),

        "architecture.md": """
Create a formal architecture document for GES-POC.

Required title:
# System Architecture

Required sections:
1. Architecture Overview
   1.1 High-Level Architecture
   1.2 Service Interaction Map
2. GCP Services and Responsibilities
3. Repository Structure
4. End-to-End Data Flow
5. Design Considerations

Diagram requirements:
- Under '1.1 High-Level Architecture', include exactly one Mermaid flowchart in a fenced code block
- Under '1.2 Service Interaction Map', include exactly one Mermaid flowchart in a fenced code block
- Under '4. End-to-End Data Flow', include exactly one Mermaid sequenceDiagram in a fenced code block
- Mermaid blocks must start with ```mermaid
- Use valid Mermaid syntax only
- Do not place diagram syntax outside fenced blocks

Diagram component guidance:
Use repository-supported components such as:
User, Streamlit App, Cloud Run, Google Cloud Storage, Speech-to-Text, DLP, BigQuery, Looker Studio

Important:
- The diagrams must render in MkDocs with Mermaid support
- Use node syntax like A[Label]
- Use flowchart TD for flowcharts
""".strip(),

        "deployment.md": """
Create a formal deployment guide for GES-POC.

Required title:
# Deployment Guide

Required sections:
1. Deployment Overview
2. Local Development Setup
3. Authentication and Credentials
4. Docker Build Process
5. Cloud Build Workflow
6. Cloud Run Deployment
7. BigQuery and Reporting Integration
8. Validation and Smoke Checks
9. Operational Notes

Content expectations:
- Use the repository context to describe containerization and deployment
- Reference Cloud Build and Dockerfile behavior if present in the context
- Keep the instructions structured and implementation-focused
""".strip(),

        "troubleshooting.md": """
Create a formal troubleshooting guide for GES-POC.

Required title:
# Troubleshooting Guide

Required sections:
1. Build Failures
2. Deployment Failures
3. Authentication and Permission Issues
4. Vertex AI / Gemini Integration Issues
5. Cloud Run Runtime Issues
6. BigQuery and Reporting Issues
7. Recommended Debugging Workflow

For each issue area:
- Describe symptoms
- Describe likely causes
- Describe resolution steps

Content expectations:
- Keep it specific to this project type
- Use practical issue/cause/resolution language
- Avoid generic filler
""".strip(),

        "history.md": f"""
Create a formal version history document for GES-POC.

Required title:
# Version History

Required sections:
1. Change Log Summary
2. Recent Repository History
3. Release Notes Style Summary

Requirements:
- Use Markdown tables where useful
- Base the content on this git history:
{history}
- If history is limited, say that the available history is limited
- Keep the wording formal and release-note oriented
""".strip(),
    }

    for filename, task in sections.items():
        print(f"✍️ AI is writing {filename}...", flush=True)
        try:
            # Slightly narrower context per page for better output quality
            if filename == "history.md":
                page_context = "Repository git history and current project context.\n" + context[:6000]
            elif filename == "architecture.md":
                page_context = context
            elif filename == "deployment.md":
                page_context = context
            else:
                page_context = context[:12000]

            text = generate_markdown(client, task, page_context).strip()

            if not text:
                text = f"# {filename}\nNo content generated."

            write_file(os.path.join("docs", filename), text)
            print(f"✅ Successfully created {filename}", flush=True)

        except Exception as e:
            print(f"⚠️ Error generating {filename}: {e}", flush=True)
            write_file(
                os.path.join("docs", filename),
                f"# {filename}\nAuto-generation failed: {e}\n"
            )


if __name__ == "__main__":
    generate_docs()
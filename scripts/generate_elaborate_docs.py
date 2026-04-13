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
        cmd = ["git", "log", "-n", "5", "--pretty=format:%h - %ad: %s", "--date=short"]
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
    return context

def generate_docs():
    client = get_client()
    context = get_repo_context()
    history = get_git_history()

    os.makedirs("docs", exist_ok=True)

    sections = {
        "index.md": "Write an elaborate technical overview for the GES-POC project.",
        "architecture.md": "Generate a technical architecture guide with a Mermaid diagram.",
        "deployment.md": "Write a deployment guide based on the repository context and cloudbuild.yaml.",
        "history.md": f"Summarize this git history into a Markdown table:\n{history}",
        "troubleshooting.md": "Write a troubleshooting guide for likely build, deploy, and runtime issues."
    }

    for filename, task in sections.items():
        print(f"✍️ AI is writing {filename}...")
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=f"""
You are writing polished technical Markdown documentation for a software project.

Repository context:
{context}

Task:
{task}

Requirements:
- Output Markdown only
- Be concrete and technical
- Do not invent services or files not present in the context
- Use headings and concise sections
""".strip()
            )

            text = response.text or f"# {filename}\nNo content generated."
            with open(os.path.join("docs", filename), "w", encoding="utf-8") as f:
                f.write(text)

            print(f"✅ Successfully created {filename}")

        except Exception as e:
            print(f"⚠️ Error generating {filename}: {e}")
            with open(os.path.join("docs", filename), "w", encoding="utf-8") as f:
                f.write(f"# {filename}\nAuto-generation failed: {e}\n")

if __name__ == "__main__":
    generate_docs()
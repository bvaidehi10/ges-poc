import os
import subprocess
import json
from google.genai import Client, types

def get_git_history():
    try:
        cmd = ["git", "log", "-n", "5", "--pretty=format:%h - %ad: %s", "--date=short"]
        return subprocess.check_output(cmd).decode("utf-8")
    except:
        return "Initial release."

def get_repo_context():
    files = ['app.py', 'cloudbuild.yaml', 'Dockerfile', 'requirements.txt']
    context = ""
    for f_name in files:
        if os.path.exists(f_name):
            with open(f_name, 'r') as f:
                context += f"\n--- {f_name} ---\n{f.read()}\n"
    return context

def generate_docs():
    PROJECT_ID = os.getenv("PROJECT_ID")
    if not PROJECT_ID:
        print("ERROR: PROJECT_ID is missing")
        return

    client = Client(vertexai=True, project=PROJECT_ID, location="us-central1")
    
    context = get_repo_context()
    history = get_git_history()
    
    os.makedirs('docs', exist_ok=True)
    
    sections = {
        "index.md": "Overview of the GES-POC project.",
        "architecture.md": "Architecture with Mermaid.js diagram.",
        "deployment.md": "Deployment guide.",
        "troubleshooting.md": "Troubleshooting guide.",
        "history.md": f"Version History table for: {history}"
    }

    for filename, prompt_task in sections.items():
        print(f"✍️ Writing {filename}...")
        try:
            # Using the versioned stable model ID
            response = client.models.generate_content(
                model='gemini-1.5-flash-002',
                contents=f"Context: {context}\nTask: {prompt_task}\nFormat: Elaborate technical Markdown."
            )
            with open(f"docs/{filename}", "w") as f:
                f.write(response.text)
        except Exception as e:
            print(f"⚠️ Failed to generate {filename}: {str(e)}")
            with open(f"docs/{filename}", "w") as f:
                f.write(f"# {filename}\nAuto-generation failed for this section.")

if __name__ == "__main__":
    generate_docs()
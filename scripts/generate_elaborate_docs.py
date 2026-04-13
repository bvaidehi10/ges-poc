import os
import subprocess
from google.genai import Client, types

def get_git_history():
    """Fetches the last 5 commit messages to create a version history."""
    try:
        # Gets hash, date, and subject of last 5 commits
        cmd = ["git", "log", "-n", "5", "--pretty=format:%h - %ad: %s", "--date=short"]
        return subprocess.check_output(cmd).decode("utf-8")
    except:
        return "No git history found."

def get_repo_context():
    """Reads core files to give Gemini context about the project."""
    files = ['app.py', 'cloudbuild.yaml', 'Dockerfile', 'requirements.txt']
    context = ""
    for f_name in files:
        if os.path.exists(f_name):
            with open(f_name, 'r') as f:
                context += f"\n--- {f_name} ---\n{f.read()}\n"
    return context

def generate_docs():
    PROJECT_ID = os.getenv("PROJECT_ID")
    client = Client(vertexai=True, project=PROJECT_ID, location="us-central1")
    
    context = get_repo_context()
    history = get_git_history()
    
    os.makedirs('docs', exist_ok=True)
    
    # Sections to generate
    sections = {
        "index.md": "Overview of the GES-POC project and RAG business value.",
        "architecture.md": "Technical architecture with a Mermaid.js diagram showing Cloud Build -> Cloud Run -> Vertex AI.",
        "deployment.md": "Elaborate deployment guide based on the cloudbuild.yaml file.",
        "troubleshooting.md": "Common errors and how the AI failure analysis helps debug them.",
        "history.md": f"Professional Version History based on these raw commits: {history}"
    }

    for filename, prompt_task in sections.items():
        print(f"✍️ AI is writing {filename}...")
        
        full_prompt = f"""
        Context: {context}
        Task: {prompt_task}
        Requirement: Use professional technical Markdown. For 'history.md', create a clean table with columns 'Version/Hash', 'Date', and 'Change Summary'.
        """

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=full_prompt
        )
        
        with open(f"docs/{filename}", "w") as f:
            f.write(response.text)

if __name__ == "__main__":
    generate_docs()
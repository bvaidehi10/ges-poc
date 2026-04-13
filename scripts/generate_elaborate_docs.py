import os
import subprocess
import json
from google import genai

def get_client():
    """Initializes the AI client, prioritizing the Google AI Studio API Key."""
    api_key = os.getenv("GEMINI_API_KEY")
    project_id = os.getenv("PROJECT_ID")
    
    if api_key:
        print("🚀 Using Google AI Studio API Key (Bypassing Vertex AI 404s)...")
        return genai.Client(api_key=api_key)
    else:
        print("🛡️ Using Vertex AI Service Account...")
        return genai.Client(
            vertexai=True, 
            project=project_id, 
            location="us-central1"
        )

def get_git_history():
    """Retrieves the last 5 commits for the Version History tab."""
    try:
        cmd = ["git", "log", "-n", "5", "--pretty=format:%h - %ad: %s", "--date=short"]
        return subprocess.check_output(cmd).decode("utf-8")
    except Exception:
        return "Initial release version."

def get_repo_context():
    """Reads core application files to give the AI context about your project."""
    files = ['app.py', 'cloudbuild.yaml', 'Dockerfile', 'requirements.txt']
    context = ""
    for f_name in files:
        if os.path.exists(f_name):
            try:
                with open(f_name, 'r') as f:
                    context += f"\n--- FILE: {f_name} ---\n{f.read()}\n"
            except Exception as e:
                print(f"Could not read {f_name}: {e}")
    return context

def generate_docs():
    """Generates elaborate documentation for each tab using Gemini."""
    # Ensure project ID exists for general context, though API Key doesn't strictly need it
    project_id = os.getenv("PROJECT_ID", "ges-poc-project")
    
    client = get_client()
    repo_context = get_repo_context()
    git_history = get_git_history()
    
    os.makedirs('docs', exist_ok=True)
    
    # Define the prompts for each tab
    sections = {
        "index.md": "Write an ELOBORATE overview. Explain the value of this Generative AI Search tool.",
        "architecture.md": "Create a deep-dive Architecture guide. Include a Mermaid.js diagram (graph TD) showing the flow.",
        "deployment.md": "Write a detailed Deployment guide based on the cloudbuild.yaml steps.",
        "troubleshooting.md": "Write a guide for common errors like IAM, Build failures, and Model 404s.",
        "history.md": f"Summarize this git history into a professional table: {git_history}"
    }

    # Iterate and generate
    for filename, prompt_task in sections.items():
        print(f"✍️ AI is writing {filename}...")
        try:
            # Use the stable model name
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"Project Context:\n{repo_context}\n\nTask: {prompt_task}\n\nFormat: Extensive Markdown."
            )
            
            with open(f"docs/{filename}", "w") as f:
                f.write(response.text)
        except Exception as e:
            print(f"⚠️ Failed to generate {filename}: {str(e)}")
            with open(f"docs/{filename}", "w") as f:
                f.write(f"# {filename}\nAuto-generation failed: {str(e)}")

if __name__ == "__main__":
    generate_docs()
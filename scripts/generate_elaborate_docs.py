import os
import subprocess
from google import genai

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client(vertexai=True, project=os.getenv("PROJECT_ID"), location="us-central1")

def generate_docs():
    client = get_client()
    model_id = 'models/gemini-1.5-flash' if os.getenv("GEMINI_API_KEY") else 'gemini-1.5-flash'
    
    # Use absolute path relative to the script's root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, 'docs')
    os.makedirs(docs_dir, exist_ok=True)

    sections = {
        "index.md": "Write an ELOBORATE project overview.",
        "architecture.md": "Generate an architecture guide with Mermaid.js.",
        "deployment.md": "Write a deployment guide.",
        "history.md": "Summarize the git history into a table.",
        "troubleshooting.md": "Write a troubleshooting guide."
    }

    for filename, task in sections.items():
        print(f"✍️ AI is writing {filename} to {docs_dir}...")
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=task
            )
            content = response.text
        except Exception as e:
            content = f"# {filename}\nGeneration failed: {e}"

        with open(os.path.join(docs_dir, filename), 'w') as f:
            f.write(content)

if __name__ == "__main__":
    generate_docs()
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
    
    os.makedirs('docs', exist_ok=True)
    sections = {
        "index.md": "Overview of GES-POC and RAG value.",
        "architecture.md": "Architecture with Mermaid diagram (graph TD).",
        "deployment.md": "Step-by-step deployment guide.",
        "history.md": "Version History table.",
        "troubleshooting.md": "Troubleshooting guide."
    }

    for filename, task in sections.items():
        print(f"✍️ AI is writing {filename}...")
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=f"Generate elaborate technical documentation for {filename}. Task: {task}"
            )
            content = response.text
        except Exception as e:
            content = f"# {filename}\nAI generation failed: {e}"

        with open(os.path.join('docs', filename), 'w') as f:
            f.write(content)

if __name__ == "__main__":
    generate_docs()
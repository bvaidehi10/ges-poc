import os
import subprocess
from google import genai

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    project_id = os.getenv("PROJECT_ID")
    
    if api_key:
        print("🚀 Using Google AI Studio API Key...")
        # For AI Studio, we do NOT set vertexai=True
        return genai.Client(api_key=api_key)
    else:
        print("🛡️ Using Vertex AI Service Account...")
        return genai.Client(
            vertexai=True, 
            project=project_id, 
            location="us-central1"
        )

def generate_docs():
    client = get_client()
    
    # FIX: The SDK handles the 'models/' prefix automatically for AI Studio.
    # Using 'gemini-1.5-flash' is the most compatible string for the v1 stable API.
    model_id = 'gemini-1.5-flash'
    
    os.makedirs('docs', exist_ok=True)
    sections = {
        "index.md": "Write an ELOBORATE project overview for GES-POC.",
        "architecture.md": "Generate an architecture guide with a Mermaid.js diagram.",
        "deployment.md": "Write a deployment guide based on cloudbuild.yaml.",
        "history.md": "Summarize the git history into a table.",
        "troubleshooting.md": "Write a troubleshooting guide for common errors."
    }

    for filename, task in sections.items():
        print(f"✍️ AI is writing {filename}...")
        try:
            # We call the model directly
            response = client.models.generate_content(
                model=model_id,
                contents=task
            )
            content = response.text
            if not content:
                content = f"# {filename}\nAI returned an empty response."
        except Exception as e:
            print(f"⚠️ Error generating {filename}: {e}")
            content = f"# {filename}\nGeneration failed: {e}"

        with open(os.path.join('docs', filename), 'w') as f:
            f.write(content)

if __name__ == "__main__":
    generate_docs()
import os
import subprocess
from google import genai

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        print("🚀 Using Google AI Studio API Key...")
        return genai.Client(api_key=api_key)
    else:
        print("🛡️ Using Vertex AI Service Account...")
        return genai.Client(vertexai=True, project=os.getenv("PROJECT_ID"), location="us-central1")

def find_model(client):
    """Lists models and finds the correct ID for Gemini 1.5 Flash."""
    try:
        print("🔍 Querying available models...")
        for model in client.models.list():
            # Look for the flash model in the list
            if "gemini-1.5-flash" in model.name:
                print(f"✅ Found model: {model.name}")
                return model.name
    except Exception as e:
        print(f"⚠️ Could not list models: {e}")
    
    # Fallback to the most standard string if listing fails
    return 'gemini-1.5-flash'

def generate_docs():
    client = get_client()
    
    # SELF-HEALING: Dynamically find the model name
    model_id = find_model(client)
    
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
            response = client.models.generate_content(
                model=model_id,
                contents=task
            )
            if response.text:
                with open(os.path.join('docs', filename), 'w') as f:
                    f.write(response.text)
                print(f"✅ Successfully created {filename}")
            else:
                print(f"⚠️ AI returned empty text for {filename}")
        except Exception as e:
            print(f"⚠️ Error generating {filename}: {e}")
            # Ensure file exists to prevent MkDocs 404
            with open(os.path.join('docs', filename), 'w') as f:
                f.write(f"# {filename}\nAuto-generation failed: {e}")

if __name__ == "__main__":
    generate_docs()
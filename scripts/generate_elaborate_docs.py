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

def generate_docs():
    client = get_client()
    api_key = os.getenv("GEMINI_API_KEY")
    
    # FIX: Use 'models/' prefix for AI Studio API Key mode
    model_id = 'models/gemini-1.5-flash' if api_key else 'gemini-1.5-flash'
    
    os.makedirs('docs', exist_ok=True)
    sections = ["index.md", "architecture.md", "deployment.md", "history.md", "troubleshooting.md"]

    for section in sections:
        print(f"✍️ AI is writing {section}...")
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=f"Write elaborate technical documentation for the file {section}."
            )
            with open(f"docs/{section}", "w") as f:
                f.write(response.text)
        except Exception as e:
            print(f"⚠️ Failed {section}: {str(e)}")

if __name__ == "__main__":
    generate_docs()
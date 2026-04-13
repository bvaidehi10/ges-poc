import os
import json
import time
import sys
from google.genai import Client, types
from google.cloud import devtools_build_v1 as build_v1

def wait_for_build_completion(client, project_id, build_id):
    """Polls the build status until it is no longer 'WORKING'."""
    print(f"🔎 Monitoring build {build_id}...")
    for _ in range(30): # Poll for 5 minutes (10s * 30)
        build = client.get_build(project_id=project_id, id=build_id)
        # Status 2 is 'WORKING'. We wait until it's 3 (FAILURE), 4 (INTERNAL_ERROR), or 5 (TIMEOUT)
        if build.status not in [1, 2]: 
            return build
        time.sleep(10)
    return None

def run_analysis():
    PROJECT = os.getenv("PROJECT_ID")
    BUILD_ID = os.getenv("BUILD_ID")
    
    build_client = build_v1.CloudBuildClient()
    build = wait_for_build_completion(build_client, PROJECT, BUILD_ID)
    
    if not build or build.status not in [3, 4, 5]:
        print("✅ Build finished successfully or timed out. No AI analysis needed.")
        return

    print("❌ Failure detected. Summarizing logs for Gemini 2.0...")
    
    # Collect failure context
    log_context = [f"Build Status: {build.status.name}"]
    if build.failure_info:
        log_context.append(f"Detail: {build.failure_info.detail}")
    
    for step in build.steps:
        if step.status > 2: # Capture failed steps
            log_context.append(f"Failed Step {step.id}: {step.status.name}")

    # Call Gemini 2.0 Flash
    ai_client = Client(vertexai=True, project=PROJECT, location="us-central1")
    prompt = f"Analyze these GCP Build logs and return the required JSON: {chr(10).join(log_context)}"
    
    response = ai_client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type='application/json')
    )
    
    print("\n--- AI ANALYSIS RESULT ---")
    print(response.text)
    print("--------------------------")

if __name__ == "__main__":
    run_analysis()
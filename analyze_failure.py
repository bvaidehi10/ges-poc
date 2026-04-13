import os
import json
import time
import sys
from google.genai import Client, types
from google.cloud import devtools_build_v1 as build_v1

def get_failed_log_context(project_id, build_id):
    """Fetches real-time log metadata from the current build execution."""
    client = build_v1.CloudBuildClient()
    # Give the other steps a moment to write their failure logs
    time.sleep(10) 
    
    build = client.get_build(project_id=project_id, id=build_id)
    
    log_context = []
    for step in build.steps:
        # Status 3 = FAILURE
        status_str = "FAILED" if step.status == 3 else "SUCCESS"
        log_context.append(f"Step: {step.id} | Status: {status_str}")
    
    if build.failure_info:
        log_context.append(f"TECHNICAL_FAILURE_DETAIL: {build.failure_info.detail}")
        
    return "\n".join(log_context)

def analyze_with_gemini_2_0(logs):
    """Uses Gemini 2.0 Flash to generate the structured JSON report."""
    # Initialize the modern Client
    client = Client(vertexai=True, project=os.environ["PROJECT_ID"], location="us-central1")
    
    prompt = f"""
    You are an expert DevOps AI. Analyze these Google Cloud Build logs.
    
    LOGS:
    {logs}

    Identify the failure and return ONLY a JSON object with this exact structure:
    {{
      "summary": "Short human-readable summary",
      "root_cause": "The specific technical reason",
      "issue_category": "dependency | iam_permission | code_error | infrastructure | timeout",
      "confidence": "high | medium | low",
      "recommended_fix": "Step-by-step fix"
    }}
    """

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
        )
    )
    return response.text

if __name__ == "__main__":
    PROJECT = os.getenv("PROJECT_ID")
    BUILD = os.getenv("BUILD_ID")

    try:
        context = get_failed_log_context(PROJECT, BUILD)
        # Only analyze if there is an actual failure in the context
        if "FAILED" in context or "TECHNICAL_FAILURE_DETAIL" in context:
            analysis = analyze_with_gemini_2_0(context)
            print(analysis)
        else:
            print(json.dumps({"info": "No failure detected in current build steps."}))
    except Exception as e:
        print(json.dumps({"summary": "Analyzer Error", "root_cause": str(e)}))
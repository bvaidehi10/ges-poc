# import os
# import json
# import sys
# from google.cloud import devtools_build_v1 as build_v1
# from vertexai.generative_models import GenerativeModel, GenerationConfig
# import vertexai

# def get_build_logs(project_id, build_id):
#     """Fetches real logs from the Cloud Build API for the failed build."""
#     client = build_v1.CloudBuildClient()
#     build = client.get_build(project_id=project_id, id=build_id)
    
#     # We aggregate logs from the build steps
#     # In a real-world scenario, logs are stored in GCS; 
#     # for this POC, we'll extract the 'failure_info' or 'status_detail'
#     log_summary = f"Build Status: {build.status}\n"
#     for step in build.steps:
#         log_summary += f"Step {step.id}: {step.status}\n"
    
#     if build.failure_info:
#         log_summary += f"Failure Detail: {build.failure_info.detail}\n"
        
#     return log_summary

# def analyze_with_gemini(log_text):
#     """Analyzes logs using Gemini 2.0 Flash with JSON response schema."""
#     vertexai.init(project=os.getenv("PROJECT_ID"), location="us-central1")
    
#     # Using the latest Gemini 2.0 Flash model
#     model = GenerativeModel("gemini-2.0-flash-001")
    
#     prompt = f"""
#     Analyze the following Google Cloud Build logs and identify why the deployment failed.
#     LOGS:
#     {log_text}

#     Return a JSON object with this exact structure:
#     {{
#       "summary": "Short description of the error",
#       "root_cause": "The deep technical reason for failure",
#       "issue_category": "One of: dependency, iam_permission, code_error, infrastructure, timeout",
#       "confidence": "high/medium/low",
#       "recommended_fix": "Clear step-by-step instruction to fix the issue"
#     }}
#     """

#     # Enforce JSON output mode
#     response = model.generate_content(
#         prompt,
#         generation_config=GenerationConfig(
#             response_mime_type="application/json"
#         )
#     )
    
#     return response.text

# if __name__ == "__main__":
#     # Cloud Build automatically provides BUILD_ID and PROJECT_ID
#     PROJECT_ID = os.getenv("PROJECT_ID")
#     BUILD_ID = os.getenv("BUILD_ID")

#     if not BUILD_ID:
#         print(json.dumps({"error": "No BUILD_ID found"}))
#         sys.exit(0)

#     try:
#         raw_logs = get_build_logs(PROJECT_ID, BUILD_ID)
#         analysis_json = analyze_with_gemini(raw_logs)
#         print(analysis_json)
#     except Exception as e:
#         print(json.dumps({"error": str(e)}))
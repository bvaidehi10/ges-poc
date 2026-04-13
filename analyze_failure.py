import os
import json
import sys
from google.genai import Client, types
from google.cloud import devtools_build_v1 as build_v1

FAILED_STATUSES = {3, 4, 5, 6, 7}  # FAILURE, INTERNAL_ERROR, TIMEOUT, CANCELLED, EXPIRED


def get_build_summary(project_id, build_id):
    """Fetches current build summary once, without polling."""
    client = build_v1.CloudBuildClient()
    build = client.get_build(project_id=project_id, id=build_id)

    log_context = [f"Build Status: {build.status.name if hasattr(build.status, 'name') else build.status}"]

    if getattr(build, "failure_info", None) and getattr(build.failure_info, "detail", None):
        log_context.append(f"Failure Detail: {build.failure_info.detail}")

    failed_found = False
    for step in build.steps:
        step_status = step.status
        step_name = step.id or "unnamed-step"

        log_context.append(
            f"Step {step_name}: {step_status.name if hasattr(step_status, 'name') else step_status}"
        )

        if int(step_status) in FAILED_STATUSES:
            failed_found = True

    return "\n".join(log_context), failed_found


def analyze_with_gemini(project_id, log_text):
    """Analyzes logs using Gemini and returns JSON text."""
    ai_client = Client(vertexai=True, project=project_id, location="us-central1")

    prompt = f"""
Analyze the following Google Cloud Build failure summary.

Return ONLY JSON with this exact structure:
{{
  "summary": "Short description of the error",
  "root_cause": "The technical reason for failure",
  "issue_category": "One of: dependency, iam_permission, code_error, infrastructure, timeout, docker, deployment, unknown",
  "confidence": "high/medium/low",
  "recommended_fix": "Clear instruction to fix the issue"
}}

Rules:
- Be concise
- Do not invent facts
- Base the answer only on the provided summary

SUMMARY:
{log_text}
""".strip()

    response = ai_client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json'
        )
    )

    return response.text


if __name__ == "__main__":
    project_id = os.getenv("PROJECT_ID")
    build_id = os.getenv("BUILD_ID")

    if not project_id or not build_id:
        print(json.dumps({"error": "PROJECT_ID and BUILD_ID are required"}))
        sys.exit(1)

    try:
        summary, failed_found = get_build_summary(project_id, build_id)

        if not failed_found:
            print(json.dumps({
                "summary": "No failed step detected",
                "root_cause": "Build may still be running or succeeded",
                "issue_category": "unknown",
                "confidence": "low",
                "recommended_fix": "Check build ordering and allowFailure settings"
            }))
            sys.exit(0)

        result = analyze_with_gemini(project_id, summary)
        print("\n--- AI ANALYSIS RESULT ---")
        print(result)
        print("--------------------------")

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
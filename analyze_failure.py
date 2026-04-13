import os
import json
import sys
from pathlib import Path

from google import genai
from google.genai.types import HttpOptions

WORKSPACE = Path("/workspace")
MAX_CHARS = 8000


def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def tail_text(text: str, max_chars: int = MAX_CHARS) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def main() -> int:
    print("🔍 AI Analyzer started...")

    failed_stage = read_file(WORKSPACE / "failed_stage").strip()
    build_log = tail_text(read_file(WORKSPACE / "build.log"))
    push_log = tail_text(read_file(WORKSPACE / "push.log"))
    deploy_log = tail_text(read_file(WORKSPACE / "deploy.log"))

    if not failed_stage:
        print(json.dumps({
            "summary": "No failure detected",
            "root_cause": "No failed_stage file found in /workspace",
            "issue_category": "unknown",
            "confidence": "low",
            "recommended_fix": "Check the earlier Cloud Build steps that should write /workspace/failed_stage"
        }, indent=2))
        return 0

    print(f"❌ Detected failure in stage: {failed_stage}")
    print("📄 Sending logs to Gemini...")

    log_bundle_parts = [f"FAILED_STAGE: {failed_stage}"]
    if build_log:
        log_bundle_parts.append(f"=== BUILD LOG ===\n{build_log}")
    if push_log:
        log_bundle_parts.append(f"=== PUSH LOG ===\n{push_log}")
    if deploy_log:
        log_bundle_parts.append(f"=== DEPLOY LOG ===\n{deploy_log}")

    log_bundle = "\n\n".join(log_bundle_parts)

    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT or PROJECT_ID is required")

        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "global"),
            http_options=HttpOptions(api_version="v1"),
        )

        prompt = f"""
You are a senior Google Cloud DevOps engineer.

Analyze the following Cloud Build failure logs.

Return ONLY valid JSON with this exact structure:
{{
  "summary": "Short description of the failure",
  "root_cause": "Most likely technical cause based only on log evidence",
  "issue_category": "One of: dependency, docker, iam_permission, code_error, infrastructure, timeout, config, deployment, unknown",
  "confidence": "high/medium/low",
  "recommended_fix": "Clear step-by-step fix"
}}

Rules:
- Use only the evidence in the logs.
- Do not invent missing facts.
- If later stages were skipped, focus on the real failed stage.

LOGS:
{log_bundle}
""".strip()

        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )

        print("🤖 AI RESULT:")
        print(response.text)

    except Exception as e:
        print(json.dumps({
            "summary": "AI analysis step failed",
            "root_cause": str(e),
            "issue_category": "unknown",
            "confidence": "low",
            "recommended_fix": "Check Vertex AI auth, environment variables, and model access"
        }, indent=2))
        return 1

    # Keep overall build failed after analysis
    return 1


if __name__ == "__main__":
    sys.exit(main())
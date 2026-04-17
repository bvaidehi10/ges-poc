import os
import re
import subprocess
from google import genai

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def get_client():
    """Initializes the Vertex AI client using ADC / service account."""
    project_id = os.getenv("PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("❌ PROJECT_ID or GOOGLE_CLOUD_PROJECT environment variable is missing!")

    print(f"🛡️ Initializing Vertex AI for Project: {project_id}")
    return genai.Client(
        vertexai=True,
        project=project_id,
        location="global",
    )


def get_git_history():
    try:
        cmd = ["git", "log", "-n", "8", "--pretty=format:%h | %ad | %s", "--date=short"]
        return subprocess.check_output(cmd).decode("utf-8")
    except Exception:
        return "Initial release."


def get_repo_context():
    """
    Build repo context from important root files plus relevant folders like services/.
    """
    root_files = [
        "app.py",
        "cloudbuild.yaml",
        "Dockerfile",
        "requirements.txt",
        "mkdocs.yml",
        "README.md",
    ]

    folders_to_scan = [
        "services",
        "utils",
        "pages",
        "components",
        "src",
    ]

    allowed_extensions = {".py", ".yaml", ".yml", ".md", ".txt"}
    max_total_chars = 50000
    max_file_chars = 5000

    context_parts = []
    total_chars = 0

    def add_file(file_path: str):
        nonlocal total_chars

        if not os.path.exists(file_path) or total_chars >= max_total_chars:
            return

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()[:max_file_chars]

            block = f"\n--- {file_path} ---\n{content}\n"
            if total_chars + len(block) <= max_total_chars:
                context_parts.append(block)
                total_chars += len(block)
        except Exception:
            pass

    for file_name in root_files:
        add_file(file_name)

    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            continue

        for root, _, files in os.walk(folder):
            for name in sorted(files):
                _, ext = os.path.splitext(name)
                if ext.lower() not in allowed_extensions:
                    continue

                add_file(os.path.join(root, name))

                if total_chars >= max_total_chars:
                    break
            if total_chars >= max_total_chars:
                break

    return "".join(context_parts)


def write_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def dedent_fenced_mermaid_blocks(text: str) -> str:
    """
    Removes leading indentation before fenced Mermaid blocks so MkDocs
    treats them as fenced code blocks, not indented code.
    """
    lines = text.splitlines()
    out = []
    inside_mermaid = False

    for line in lines:
        stripped = line.lstrip()

        if stripped.startswith("```mermaid"):
            inside_mermaid = True
            out.append("```mermaid")
            continue

        if inside_mermaid and stripped.startswith("```"):
            inside_mermaid = False
            out.append("```")
            continue

        if inside_mermaid:
            out.append(stripped)
        else:
            out.append(line)

    return "\n".join(out)


def convert_indented_mermaid_to_fences(text: str) -> str:
    """
    Converts Mermaid diagrams written as indented code blocks into fenced ```mermaid blocks.
    This fixes pages where Mermaid shows up as plain text/code.
    """
    lines = text.splitlines()
    result = []
    i = 0

    mermaid_starters = ("flowchart ", "graph ", "sequenceDiagram")

    while i < len(lines):
        line = lines[i]

        # detect indented mermaid starter
        if line.startswith("    ") and line.strip().startswith(mermaid_starters):
            block = [line.strip()]
            i += 1

            while i < len(lines):
                next_line = lines[i]

                # continue only while still indented code or blank line within block
                if next_line.startswith("    "):
                    block.append(next_line.strip())
                    i += 1
                    continue

                if next_line.strip() == "":
                    break

                break

            result.append("```mermaid")
            result.extend(block)
            result.append("```")
            continue

        result.append(line)
        i += 1

    return "\n".join(result)


def wrap_bare_mermaid_blocks(text: str) -> str:
    """
    Wraps bare Mermaid diagram sections into fenced ```mermaid blocks if AI forgot fences.
    """
    lines = text.splitlines()
    result = []
    i = 0
    mermaid_starters = ("flowchart ", "graph ", "sequenceDiagram")

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if stripped.startswith(mermaid_starters):
            block = [stripped]
            i += 1

            while i < len(lines):
                next_line = lines[i].rstrip()

                if next_line.strip().startswith("#"):
                    break

                if next_line.strip() == "":
                    break

                block.append(next_line.strip())
                i += 1

            result.append("```mermaid")
            result.extend(block)
            result.append("```")
            continue

        result.append(line)
        i += 1

    return "\n".join(result)


def sanitize_mermaid_blocks(text: str) -> str:
    pattern = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)

    def clean_block(match):
        block = match.group(1).strip()
        lines = block.splitlines()

        if not lines:
            return "```mermaid\n```"

        first_line = lines[0].strip()
        first_line = re.sub(r"^graph\s+TD\b", "flowchart TD", first_line)

        cleaned_lines = [first_line]

        for raw_line in lines[1:]:
            line = raw_line.strip()

            if not line:
                continue

            line = re.sub(r'\b([A-Za-z0-9_]+)\s*--\s*([A-Za-z0-9_]+)', r'\1 --> \2', line)
            line = re.sub(r'-->\|[^|]+\|', '-->', line)
            line = re.sub(r'--\s*[^-<>]+\s*-->', '-->', line)

            line = re.sub(r'(\b[A-Za-z0-9_]+)\{([^}]+)\}', r'\1[\2]', line)
            line = re.sub(r'(\b[A-Za-z0-9_]+)\(([^)]+)\)', r'\1[\2]', line)

            line = line.replace(";", "")
            line = line.replace("<", "").replace(">", "")

            def clean_label(m):
                node_id = m.group(1)
                label = m.group(2)
                label = re.sub(r"[():{}]", "", label)
                label = re.sub(r"\s+", " ", label).strip()
                return f"{node_id}[{label}]"

            line = re.sub(r'(\b[A-Za-z0-9_]+)\[([^\]]+)\]', clean_label, line)

            cleaned_lines.append(line)

        return "```mermaid\n" + "\n".join(cleaned_lines) + "\n```"

    return pattern.sub(clean_block, text)


def generate_markdown(client, task, context):
    """Sends the request to Vertex AI."""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"""
You are writing enterprise-style technical documentation for a Google Cloud proof-of-concept project.

Repository context:
{context}

Task:
{task}

Global writing rules:
- Output Markdown only
- Use a formal technical documentation tone
- Do not write like a chatbot
- Do not use casual wording
- Prefer numbered sections and subsections
- Be specific to the repository context
- Do not invent services, modules, files, or deployment steps not supported by the context
- Prefer precise implementation details over generic statements
- Use clean headings, short paragraphs, and concise tables where appropriate
- Where diagrams are requested, output valid Mermaid fenced code blocks only
- Never output Mermaid syntax as plain paragraph text
- Do not wrap the whole response in triple backticks

STRICT MERMAID RULES FOR FLOWCHARTS:
- Use only: flowchart TD or flowchart LR
- Use only rectangle nodes in the form A[Label]
- Do not use decision nodes like A{{Decision}}
- Do not use rounded nodes like A(Text)
- Do not use edge labels like -->|text|
- Keep labels short and simple
- Avoid special characters such as ; : {{ }} ( ) < >
- Prefer simple chains and branches only
- Use consistent node IDs
""".strip()
    )
    return response.text or ""


def generate_docs():
    client = get_client()
    context = get_repo_context()
    history = get_git_history()

    os.makedirs("docs", exist_ok=True)

    sections = {
        "index.md": """
Create the main landing page for GES-POC in the style of a formal technical documentation site.

Required title:
# GES Audio Processing POC - Technical Documentation

Required sections:
## 1. Executive Summary
## 2. Business Objective
## 3. Scope of the POC
## 4. Key Capabilities
## 5. Technology Stack
## 6. Repository Overview
## 7. Operational Flow Summary
""".strip(),

        "architecture.md": """
Create a formal architecture document for GES-POC, similar in depth and structure to an enterprise architecture page.

Required title:
# System Architecture

Required sections:
## 1. Architecture Overview
### 1.1 High-Level Architecture
- Write a short introduction
- Include exactly one Mermaid flowchart in a fenced code block

### 1.2 Service Interaction Map
- Write a short introduction
- Include exactly one Mermaid flowchart in a fenced code block

## 2. GCP Services & Responsibilities
- Provide a Markdown table with columns:
  Service | Responsibility | Notes

## 3. Repository Structure
- Explain the major folders and files, especially app entry point and services folder usage

## 4. Data Flow
- Write a short introduction
- Include exactly one Mermaid sequenceDiagram in a fenced code block

## 5. Design Considerations
- Cover maintainability, scalability, security, and observability

Important:
- The content must reflect the actual repository context, including any relevant services/helper files
- The diagrams must be browser-renderable Mermaid
- Use concise but meaningful labels
""".strip(),

        "deployment.md": """
Create a formal deployment guide for GES-POC.

Required title:
# Deployment Guide

Required sections:
## 1. Deployment Overview
## 2. Local Development Setup
## 3. Authentication and Credentials
## 4. Docker Build Process
## 5. Cloud Build Workflow
## 6. Cloud Run Deployment
## 7. BigQuery and Reporting Integration
## 8. Validation and Smoke Checks
## 9. Operational Notes
""".strip(),

        "troubleshooting.md": """
Create a formal troubleshooting guide for GES-POC.

Required title:
# Troubleshooting Guide

Required sections:
## 1. Build Failures
## 2. Deployment Failures
## 3. Authentication and Permission Issues
## 4. Vertex AI / Gemini Integration Issues
## 5. Cloud Run Runtime Issues
## 6. BigQuery and Reporting Issues
## 7. Recommended Debugging Workflow
""".strip(),

        "history.md": f"""
Create a formal version history document for GES-POC.

Required title:
# Version History

Required sections:
## 1. Change Log Summary
## 2. Recent Repository History
## 3. Release Notes Style Summary

Requirements:
- Use Markdown tables where useful
- Base the content on this git history:
{history}
""".strip(),
    }

    for filename, task in sections.items():
        print(f"✍️ AI is writing {filename} via Vertex AI...", flush=True)
        try:
            if filename == "history.md":
                page_context = "Repository git history and current project context.\n" + context[:6000]
            elif filename in ("architecture.md", "deployment.md"):
                page_context = context
            else:
                page_context = context[:14000]

            text = generate_markdown(client, task, page_context).strip()
            text = convert_indented_mermaid_to_fences(text)
            text = wrap_bare_mermaid_blocks(text)
            text = dedent_fenced_mermaid_blocks(text)
            text = sanitize_mermaid_blocks(text)

            if not text:
                text = f"# {filename}\nNo content generated."

            write_file(os.path.join("docs", filename), text)
            print(f"✅ Successfully created {filename}", flush=True)

        except Exception as e:
            error_str = str(e)
            print(f"⚠️ Error generating {filename}: {error_str}", flush=True)

            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                print("🚫 Quota exhausted. Stopping further AI doc generation.", flush=True)
                break

            print(f"⏭️ Keeping existing docs/{filename} if present", flush=True)
            if not os.path.exists(os.path.join("docs", filename)):
                write_file(
                    os.path.join("docs", filename),
                    f"# {filename}\nAuto-generation failed: {error_str}\n"
                )


if __name__ == "__main__":
    generate_docs()
import os
import textwrap
import subprocess
from PIL import Image, ImageDraw, ImageFont
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


def ensure_dirs():
    os.makedirs("docs", exist_ok=True)
    os.makedirs("docs/assets", exist_ok=True)


def generate_markdown(client, task, context):
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
- Use clean headings, short paragraphs, bullets, and tables where appropriate
- Do not output Mermaid
- Do not wrap the whole response in triple backticks
""".strip()
    )
    return response.text or ""


def get_font(size=22, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_wrapped_text(draw, text, box, font, fill, align="center", line_spacing=6):
    x1, y1, x2, y2 = box
    max_width = x2 - x1 - 20

    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])

    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)
    y = y1 + ((y2 - y1) - total_height) / 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]

        if align == "center":
            x = x1 + ((x2 - x1) - line_width) / 2
        else:
            x = x1 + 10

        draw.text((x, y), line, font=font, fill=fill)
        y += line_heights[i] + line_spacing


def draw_rounded_box(draw, box, fill, outline, radius=24, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_vertical_flow_diagram(output_path: str, steps, title: str, subtitle: str = ""):
    width, height = 1400, 1900
    bg_top = (246, 248, 252)
    bg_bottom = (232, 238, 248)

    img = Image.new("RGB", (width, height), bg_top)
    draw = ImageDraw.Draw(img)

    # subtle vertical gradient
    for y in range(height):
        ratio = y / height
        r = int(bg_top[0] * (1 - ratio) + bg_bottom[0] * ratio)
        g = int(bg_top[1] * (1 - ratio) + bg_bottom[1] * ratio)
        b = int(bg_top[2] * (1 - ratio) + bg_bottom[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    title_font = get_font(42, bold=True)
    subtitle_font = get_font(22, bold=False)
    box_font = get_font(28, bold=True)

    draw.text((80, 50), title, font=title_font, fill=(15, 23, 42))
    if subtitle:
        draw.text((80, 115), subtitle, font=subtitle_font, fill=(71, 85, 105))

    x1, x2 = 180, 1220
    y = 200
    box_h = 150

    for i, step in enumerate(steps):
        text = step["text"]
        fill = step["fill"]
        outline = step.get("outline", (148, 163, 184))
        text_color = step.get("text_color", (15, 23, 42))

        box = (x1, y, x2, y + box_h)
        draw_rounded_box(draw, box, fill=fill, outline=outline, radius=28, width=3)
        draw_wrapped_text(draw, text, box, box_font, text_color)

        if i < len(steps) - 1:
            cx = (x1 + x2) // 2
            arrow_y1 = y + box_h
            arrow_y2 = arrow_y1 + 55
            draw.line((cx, arrow_y1, cx, arrow_y2), fill=(100, 116, 139), width=6)
            draw.polygon(
                [(cx - 16, arrow_y2 - 6), (cx + 16, arrow_y2 - 6), (cx, arrow_y2 + 18)],
                fill=(100, 116, 139),
            )

        y += box_h + 75

    img.save(output_path)


def generate_diagrams():
    ensure_dirs()

    high_level_steps = [
        {
            "text": "Developer Updates Repository\n(app.py, cloudbuild.yaml, services/)",
            "fill": (226, 232, 240),
        },
        {
            "text": "GitHub Actions Pipeline",
            "fill": (219, 234, 254),
        },
        {
            "text": "AI Documentation Generator\n(Gemini on Vertex AI)",
            "fill": (37, 99, 235),
            "text_color": (255, 255, 255),
            "outline": (29, 78, 216),
        },
        {
            "text": "Generate Markdown Content\n+ Architecture Diagrams",
            "fill": (209, 250, 229),
        },
        {
            "text": "MkDocs Material Build",
            "fill": (233, 213, 255),
        },
        {
            "text": "Publish to GitHub Pages",
            "fill": (199, 210, 254),
        },
        {
            "text": "Live Documentation Website",
            "fill": (167, 243, 208),
        },
    ]

    service_map_steps = [
        {
            "text": "Streamlit App",
            "fill": (219, 234, 254),
        },
        {
            "text": "services/\nBusiness Logic Layer",
            "fill": (37, 99, 235),
            "text_color": (255, 255, 255),
            "outline": (29, 78, 216),
        },
        {
            "text": "Google Cloud Storage",
            "fill": (226, 232, 240),
        },
        {
            "text": "Speech-to-Text + DLP",
            "fill": (221, 214, 254),
        },
        {
            "text": "BigQuery Analytics Layer",
            "fill": (209, 250, 229),
        },
        {
            "text": "Results in UI / Reporting",
            "fill": (254, 240, 138),
        },
    ]

    draw_vertical_flow_diagram(
        "docs/assets/high-level-architecture.png",
        high_level_steps,
        "High-Level Architecture",
        "Repository change to published documentation flow",
    )

    draw_vertical_flow_diagram(
        "docs/assets/service-interaction-map.png",
        service_map_steps,
        "Service Interaction Map",
        "Application, services layer, and GCP service relationships",
    )


def build_architecture_doc(client, context):
    prose = generate_markdown(
        client,
        """
Create a formal architecture document for GES-POC, similar in depth and style to enterprise project documentation.

Required title:
# System Architecture

Required sections:
## 1. Architecture Overview
### 1.1 High-Level Architecture
Write a short introduction for the overall platform architecture.

### 1.2 Service Interaction Map
Write a short introduction for internal module/service relationships.

## 2. GCP Services & Responsibilities
Provide a Markdown table with columns:
Service | Responsibility | Notes

## 3. Repository Structure
Explain the major folders and files, especially app entry point and services folder usage.

## 4. End-to-End Data Flow
Write a clear narrative walkthrough of the runtime flow from user interaction through processing and persistence.

## 5. Design Considerations
Cover maintainability, scalability, security, and observability.
""",
        context,
    ).strip()

    # Insert image-based diagrams + sequence diagram placeholder-free prose
    high_level_md = (
        "![High-Level Architecture](assets/high-level-architecture.png)\n\n"
    )

    service_map_md = (
        "![Service Interaction Map](assets/service-interaction-map.png)\n\n"
    )

    prose = re.sub(
        r"(### 1\.1 High-Level Architecture\s*)",
        r"\1\n" + high_level_md,
        prose,
        count=1,
        flags=re.MULTILINE,
    )

    prose = re.sub(
        r"(### 1\.2 Service Interaction Map\s*)",
        r"\1\n" + service_map_md,
        prose,
        count=1,
        flags=re.MULTILINE,
    )

    return prose


def generate_docs():
    client = get_client()
    context = get_repo_context()
    history = get_git_history()

    ensure_dirs()
    generate_diagrams()

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

Important:
- Mention that architecture visuals are included in the System Architecture page
- Keep the content polished, detailed, and specific to the repo context
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

    print("✍️ AI is writing architecture.md via Vertex AI...", flush=True)
    try:
        architecture_text = build_architecture_doc(client, context)
        if not architecture_text:
            architecture_text = "# System Architecture\nNo content generated."
        write_file(os.path.join("docs", "architecture.md"), architecture_text)
        print("✅ Successfully created architecture.md", flush=True)
    except Exception as e:
        error_str = str(e)
        print(f"⚠️ Error generating architecture.md: {error_str}", flush=True)
        if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
            print("🚫 Quota exhausted. Stopping further AI doc generation.", flush=True)
            return
        if not os.path.exists(os.path.join("docs", "architecture.md")):
            write_file(
                os.path.join("docs", "architecture.md"),
                f"# System Architecture\nAuto-generation failed: {error_str}\n"
            )

    for filename, task in sections.items():
        print(f"✍️ AI is writing {filename} via Vertex AI...", flush=True)
        try:
            if filename == "history.md":
                page_context = "Repository git history and current project context.\n" + context[:6000]
            elif filename == "deployment.md":
                page_context = context
            else:
                page_context = context[:14000]

            text = generate_markdown(client, task, page_context).strip()

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
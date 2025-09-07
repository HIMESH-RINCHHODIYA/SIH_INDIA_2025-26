import os
import openai

LOG_FILE = "app.log"
PATCH_FILE = "ai_patch.diff"
TEMPLATE_DIR = "templates"

openai.api_key = os.getenv("OPENAI_API_KEY")

def collect_errors():
    errors = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            errors += f.read()

    # Scan templates for broken HTML (very basic check)
    for root, _, files in os.walk(TEMPLATE_DIR):
        for file in files:
            if file.endswith(".html"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()
                    if "{{" in content and "}}" not in content:
                        errors += f"\n⚠️ Possible broken Jinja tag in {file}\n{content}\n"

    return errors.strip()

def generate_patch(errors):
    if not errors:
        print("✅ No errors detected. Skipping patch.")
        return

    print("🛠 Sending errors to OpenAI for fix...")

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI code fixer. Fix Python Flask backend and HTML frontend issues. Return only a unified diff patch."},
            {"role": "user", "content": f"Errors found:\n{errors}\n\nGenerate a git diff patch to fix them."}
        ]
    )

    patch = response["choices"][0]["message"]["content"]
import os
import openai

# Get API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

LOG_FILE = "app.log"
REQUEST_FILE = "ai_request.txt"
PATCH_FILE = "ai_patch.diff"

def read_file_safe(path):
    """Read a file if it exists, else return empty string."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    return ""

def main():
    errors = read_file_safe(LOG_FILE)
    request = read_file_safe(REQUEST_FILE)

    if not errors and not request:
        print("✅ Nothing to fix or request.")
        return

    prompt = f"""
You are an AI assistant for a Flask + HTML project.
Your job is to:
1. Fix code errors found in app.log.
2. Implement new feature requests from ai_request.txt.
3. Output ONLY a valid git patch (diff format).

--- Errors (from app.log) ---
{errors or "No errors found."}

--- Admin Request (from ai_request.txt) ---
{request or "No new feature request."}

Respond ONLY with a git diff patch.
    """

    print("🤖 Sending request to OpenAI...")

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    patch = response.choices[0].message.content

    if not patch or "diff" not in patch:
        print("❌ No valid patch generated.")
        return

    with open(PATCH_FILE, "w", encoding="utf-8") as f:
        f.write(patch)

    print(f"✅ Patch saved to {PATCH_FILE}")

if __name__ == "__main__":
    main()

    with open(PATCH_FILE, "w") as f:
        f.write(patch)

    print(f"✅ Patch saved to {PATCH_FILE}")

if __name__ == "__main__":
    errors = collect_errors()
    generate_patch(errors)

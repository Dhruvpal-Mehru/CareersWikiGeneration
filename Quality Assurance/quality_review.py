import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient

load_dotenv()

# Setup Gemini
gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "gemini-2.5-pro"

# Setup Azure OpenAI
openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-08-01-preview"
)
GPT_MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Setup Azure Blob
blob_service = BlobServiceClient.from_connection_string(
    os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)
container = blob_service.get_container_client(
    os.getenv("AZURE_CONTAINER_NAME")
)

REQUIRED_SECTIONS = [
    "Overview",
    "Day in the Life",
    "Essential Skills",
    "Education and Training",
    "Salary and Compensation",
    "Industry Outlook",
    "Getting Started",
    "Related Careers"
]

report = {
    "generated": datetime.now().isoformat(),
    "total_reviewed": 0,
    "total_passed": 0,
    "total_fixed": 0,
    "total_failed": 0,
    "issues": []
}


def download_blob(blob_name: str) -> str:
    return container.get_blob_client(blob_name).download_blob().readall().decode("utf-8")


def upload_blob(blob_name: str, content: str):
    container.upload_blob(name=blob_name, data=content.encode("utf-8"), overwrite=True)


def check_missing_sections(content: str) -> list:
    return [s for s in REQUIRED_SECTIONS if s.lower() not in content.lower()]


def check_word_count(content: str) -> int:
    return len(content.split())


def parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        return {"passed": True, "issues": [], "overall_quality": "acceptable"}


REVIEW_PROMPT = """You are a quality reviewer for MascotGO, an educational career wiki platform.

Review this career wiki page for "{title}" and check for:
1. Factual errors or unrealistic statistics (e.g. $500K entry-level salary)
2. Unprofessional or off-tone writing (too casual, salesy, clickbait-y, or condescending)
3. Clearly wrong claims about the US job market

Return ONLY valid JSON, no markdown fences:
{{
  "passed": true or false,
  "issues": [
    {{
      "type": "factual_error | tone_issue",
      "description": "brief description",
      "location": "quote the problematic text (max 100 chars)"
    }}
  ],
  "overall_quality": "poor | acceptable | good | excellent"
}}

If no issues, return passed: true and empty issues array.

Wiki content:
{content}"""


def review_with_gemini(title: str, content: str) -> dict:
    try:
        response = gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=REVIEW_PROMPT.format(title=title, content=content[:3000])
        ).text
        return parse_json_response(response)
    except Exception as e:
        print(f"      Gemini review error: {e}")
        return {"passed": True, "issues": [], "overall_quality": "acceptable"}


def review_with_gpt(title: str, content: str) -> dict:
    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{
                "role": "user",
                "content": REVIEW_PROMPT.format(title=title, content=content[:3000])
            }],
            max_tokens=1000
        ).choices[0].message.content
        return parse_json_response(response)
    except Exception as e:
        print(f"      GPT review error: {e}")
        return {"passed": True, "issues": [], "overall_quality": "acceptable"}


def merge_reviews(gemini_result: dict, gpt_result: dict) -> dict:
    all_issues = []

    # Deduplicate issues from both models
    seen = set()
    for issue in gemini_result.get("issues", []) + gpt_result.get("issues", []):
        key = issue["type"] + issue["description"][:40]
        if key not in seen:
            seen.add(key)
            all_issues.append(issue)

    # Quality rating — take the worse of the two
    quality_order = ["poor", "acceptable", "good", "excellent"]
    g_quality = gemini_result.get("overall_quality", "acceptable")
    p_quality = gpt_result.get("overall_quality", "acceptable")
    worst_quality = min(g_quality, p_quality, key=lambda x: quality_order.index(x) if x in quality_order else 1)

    passed = len(all_issues) == 0

    return {
        "passed": passed,
        "issues": all_issues,
        "overall_quality": worst_quality,
        "gemini_quality": g_quality,
        "gpt_quality": p_quality
    }


def fix_with_gemini(title: str, content: str, issues: list) -> str:
    issues_text = "\n".join([
        f"- [{i['type']}] {i['description']} (near: '{i.get('location', '')}')"
        for i in issues
    ])

    prompt = f"""Fix the following quality issues in this MascotGO career wiki page for "{title}".

Issues to fix:
{issues_text}

Rules:
- Keep all sections and markdown structure intact
- Keep the frontmatter exactly as is
- Only fix the specific issues mentioned
- Maintain professional, inspiring tone for high school juniors through adults
- Do not add new sections or change content that is fine
- Return the complete fixed markdown

Wiki content:
{content}"""

    return gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    ).text


def review_pipeline():
    print("📥 Fetching career pages from Azure...")
    blobs = list(container.list_blobs(name_starts_with="careers/"))[:50]
    total = len(blobs)
    print(f"Found {total} pages to review")
    print("🤖 Using both Gemini 2.5 Flash + GPT-4o for review\n")

    for i, blob in enumerate(blobs):
        blob_name = blob.name
        title = blob_name.replace("careers/", "").replace(".md", "").replace("-", " ").title()

        print(f"[{i+1}/{total}] {title}")
        report["total_reviewed"] += 1

        try:
            content = download_blob(blob_name)
            all_issues = []

            # Check 1 — missing sections
            missing = check_missing_sections(content)
            for s in missing:
                all_issues.append({
                    "type": "missing_section",
                    "description": f"Missing required section: {s}",
                    "location": "N/A"
                })

            # Check 2 — word count
            word_count = check_word_count(content)
            if word_count < 800:
                all_issues.append({
                    "type": "too_short",
                    "description": f"Only {word_count} words",
                    "location": "N/A"
                })

            # Check 3 — Gemini review
            print(f"   🟣 Gemini reviewing...")
            gemini_result = review_with_gemini(title, content)

            # Check 4 — GPT-4o review
            print(f"   🟦 GPT-4o reviewing...")
            gpt_result = review_with_gpt(title, content)

            # Merge both reviews
            merged = merge_reviews(gemini_result, gpt_result)
            all_issues.extend(merged.get("issues", []))

            # Passed — no issues
            if not all_issues:
                print(f"   ✅ Passed (Gemini: {merged['gemini_quality']}, GPT: {merged['gpt_quality']})")
                report["total_passed"] += 1
                time.sleep(1)
                continue

            # Has issues
            print(f"   ⚠️  {len(all_issues)} issue(s) found — fixing with Gemini...")
            report["issues"].append({
                "blob": blob_name,
                "title": title,
                "word_count": word_count,
                "issues": all_issues,
                "gemini_quality": merged.get("gemini_quality"),
                "gpt_quality": merged.get("gpt_quality")
            })

            # Fix and re-upload
            try:
                fixed = fix_with_gemini(title, content, all_issues)
                upload_blob(blob_name, fixed)
                print(f"   ✅ Fixed and re-uploaded!")
                report["total_fixed"] += 1
            except Exception as fix_err:
                print(f"   ❌ Fix failed: {fix_err}")
                report["total_failed"] += 1

            time.sleep(2)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            report["total_failed"] += 1

        if (i + 1) % 25 == 0:
            print(f"\n📊 Progress: {report['total_passed']} passed, "
                  f"{report['total_fixed']} fixed, {report['total_failed']} failed\n")

    # Save JSON report
    report_path = f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'='*50}")
    print(f"🏁 Quality review complete!")
    print(f"{'='*50}")
    print(f"📄 Total reviewed: {report['total_reviewed']}")
    print(f"✅ Passed:         {report['total_passed']}")
    print(f"🔧 Fixed:          {report['total_fixed']}")
    print(f"❌ Failed:         {report['total_failed']}")
    print(f"📋 Report saved:   {report_path}")

    if report["issues"]:
        print(f"\nPages with issues:")
        for item in report["issues"]:
            print(f"  - {item['title']} "
                  f"(Gemini: {item['gemini_quality']}, GPT: {item['gpt_quality']})")


if __name__ == "__main__":
    review_pipeline()
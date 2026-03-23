import json
import os
import time
from typing import Any, Dict, List

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_MODEL = "gemini-2.5-flash"
INPUT_FILE = "../Data Management/final_data.json"
BLOB_PREFIX = "careers"
SLEEP_BETWEEN_REQUESTS = 1
PROGRESS_EVERY = 50
MAX_RETRIES = 5

# ----------------------------
# Clients
# ----------------------------

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

blob_service = BlobServiceClient.from_connection_string(
    os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)
container = blob_service.get_container_client(os.getenv("AZURE_CONTAINER_NAME"))


# ----------------------------
# Azure helpers
# ----------------------------

def blob_exists(blob_path: str) -> bool:
    try:
        container.get_blob_client(blob_path).get_blob_properties()
        return True
    except Exception:
        return False


def upload_text(blob_path: str, content: str) -> None:
    container.upload_blob(
        name=blob_path,
        data=content.encode("utf-8"),
        overwrite=True
    )
    print(f"✅ Uploaded: {blob_path}")


# ----------------------------
# Gemini helpers
# ----------------------------

def call_gemini(prompt: str, retries: int = MAX_RETRIES) -> str:
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = gemini.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            text = getattr(response, "text", None)

            if not text or not text.strip():
                raise ValueError("Gemini returned empty text")

            return text.strip()

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()

            is_retryable = (
                "429" in error_msg
                or "quota" in error_msg
                or "rate" in error_msg
                or "timeout" in error_msg
                or "503" in error_msg
                or "500" in error_msg
            )

            if not is_retryable or attempt == retries:
                break

            wait_time = min(60, 2 ** attempt * 5)
            print(f"⏸️  Retryable error attempt {attempt}/{retries}: {e}")
            print(f"⏳ Waiting {wait_time}s before retry...")
            time.sleep(wait_time)

    raise last_error


def extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```json"):
        text = text.removeprefix("```json").removesuffix("```").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


# ----------------------------
# Enrichment
# ----------------------------

def build_enrichment_prompt(title: str, description: str) -> str:
    return f"""
You are a US career research analyst building a high-quality educational career wiki.

Enrich the career "{title}".
Description: "{description}"

Return ONLY valid JSON. No markdown fences. No commentary outside JSON.

Rules:
- Be specific, practical, and US-focused
- Use realistic USD salary ranges
- Keep statements grounded, avoid hype
- Prefer concise, high-signal content

Return this exact JSON schema:

{{
  "career_summary": {{
    "one_sentence_definition": "string",
    "what_they_do": ["string", "string", "string", "string"],
    "work_environment": "office | remote | hybrid | field | lab | clinical | varies",
    "typical_hours_per_week": {{"min": 0, "max": 0}},
    "travel_requirement": "none | occasional | frequent | extensive",
    "physical_demands": "sedentary | light | moderate | heavy",
    "stress_level": "low | medium | high | very high",
    "day_in_the_life": [
      "Morning: string",
      "Midday: string",
      "Afternoon: string",
      "End of day: string"
    ]
  }},
  "salary": {{
    "entry_level_usd": {{"min": 0, "max": 0}},
    "mid_level_usd": {{"min": 0, "max": 0}},
    "senior_level_usd": {{"min": 0, "max": 0}},
    "salary_by_city": [
      {{"city": "string", "avg_usd": 0}},
      {{"city": "string", "avg_usd": 0}},
      {{"city": "string", "avg_usd": 0}},
      {{"city": "string", "avg_usd": 0}},
      {{"city": "string", "avg_usd": 0}}
    ],
    "remote_salary_impact": "string",
    "notes": ["string", "string"]
  }},
  "top_industries": [
    {{"name": "string", "why_hiring": "string"}},
    {{"name": "string", "why_hiring": "string"}},
    {{"name": "string", "why_hiring": "string"}},
    {{"name": "string", "why_hiring": "string"}}
  ],
  "top_companies": [
    {{"name": "string", "type": "string"}},
    {{"name": "string", "type": "string"}},
    {{"name": "string", "type": "string"}},
    {{"name": "string", "type": "string"}},
    {{"name": "string", "type": "string"}}
  ],
  "in_demand_skills": {{
    "technical": ["string", "string", "string", "string", "string", "string"],
    "soft": ["string", "string", "string", "string"],
    "tools_and_technologies": ["string", "string", "string", "string", "string"]
  }},
  "education_pathways": {{
    "common_degrees": ["string", "string"],
    "alternative_paths": ["string", "string", "string"],
    "recommended_certifications": ["string", "string", "string"],
    "bootcamps_or_courses": ["string", "string", "string"],
    "time_to_entry_level": "string"
  }},
  "career_trajectory": {{
    "entry_titles": ["string", "string", "string"],
    "mid_titles": ["string", "string", "string"],
    "senior_titles": ["string", "string", "string"],
    "adjacent_roles": ["string", "string", "string", "string"],
    "freelance_or_consulting_potential": "low | medium | high"
  }},
  "geography": {{
    "top_us_cities": ["string", "string", "string", "string", "string"],
    "remote_friendliness": "low | medium | high",
    "visa_sponsorship_common": true
  }},
  "outlook": {{
    "future_demand": "declining | stable | growing | fast-growing",
    "automation_risk": "low | medium | high",
    "drivers_of_change": ["string", "string", "string", "string"],
    "emerging_specializations": ["string", "string", "string"]
  }},
  "interview_prep": {{
    "common_interview_questions": [
      "string", "string", "string", "string", "string"
    ],
    "what_employers_look_for": ["string", "string", "string", "string"],
    "portfolio_or_experience_signals": ["string", "string", "string", "string"]
  }},
  "getting_started": {{
    "first_30_days": ["string", "string", "string"],
    "first_60_days": ["string", "string", "string"],
    "first_90_days": ["string", "string", "string"],
    "resources": [
      {{"name": "string", "type": "book | website | course | community", "url_or_note": "string"}},
      {{"name": "string", "type": "book | website | course | community", "url_or_note": "string"}},
      {{"name": "string", "type": "book | website | course | community", "url_or_note": "string"}}
    ]
  }},
  "pros_and_cons": {{
    "pros": ["string", "string", "string", "string"],
    "cons": ["string", "string", "string", "string"]
  }},
  "related_careers": ["string", "string", "string", "string", "string", "string"]
}}
""".strip()


def normalize_enrichment(data: Dict[str, Any]) -> Dict[str, Any]:
    def safe_list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    def safe_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def safe_range(value: Any) -> Dict[str, int]:
        value = safe_dict(value)
        min_val = int(value.get("min", 0) or 0)
        max_val = int(value.get("max", 0) or 0)
        if max_val < min_val:
            min_val, max_val = max_val, min_val
        return {"min": min_val, "max": max_val}

    salary = safe_dict(data.get("salary"))

    return {
        "career_summary": safe_dict(data.get("career_summary")),
        "salary": {
            "entry_level_usd": safe_range(salary.get("entry_level_usd")),
            "mid_level_usd": safe_range(salary.get("mid_level_usd")),
            "senior_level_usd": safe_range(salary.get("senior_level_usd")),
            "salary_by_city": safe_list(salary.get("salary_by_city")),
            "remote_salary_impact": salary.get("remote_salary_impact", ""),
            "notes": safe_list(salary.get("notes")),
        },
        "top_industries": safe_list(data.get("top_industries")),
        "top_companies": safe_list(data.get("top_companies")),
        "in_demand_skills": safe_dict(data.get("in_demand_skills")),
        "education_pathways": safe_dict(data.get("education_pathways")),
        "career_trajectory": safe_dict(data.get("career_trajectory")),
        "geography": safe_dict(data.get("geography")),
        "outlook": safe_dict(data.get("outlook")),
        "interview_prep": safe_dict(data.get("interview_prep")),
        "getting_started": safe_dict(data.get("getting_started")),
        "pros_and_cons": safe_dict(data.get("pros_and_cons")),
        "related_careers": safe_list(data.get("related_careers")),
    }


def enrich_career(title: str, description: str) -> Dict[str, Any]:
    prompt = build_enrichment_prompt(title, description)
    raw_text = call_gemini(prompt)
    data = extract_json(raw_text)
    return normalize_enrichment(data)


# ----------------------------
# Wiki generation
# ----------------------------

def build_wiki_prompt(title: str, description: str, enrichment: Dict[str, Any]) -> str:
    enrichment_json = json.dumps(enrichment, indent=2)

    return f"""
You are writing a polished, high-quality educational career wiki page in markdown.

Write a comprehensive wiki page for the US career "{title}".
Description: {description}

Structured enrichment data:
{enrichment_json}

Requirements:
- Length: 2000-3000 words
- Audience: high school juniors through adults
- Tone: professional, practical, encouraging, not cheesy
- Focus on US job market, US education, US salaries
- Use enrichment data consistently throughout
- Do not mention you were given structured data
- Be concrete and actionable
- Include real employer examples
- Make it genuinely useful for someone considering this path

Use this exact frontmatter:

---
title: "{title}"
type: "career"
description: "{description}"
---

Use these exact sections in this order:

## Overview
200-300 words. Strong introduction covering what the career is,
what the work involves, work environment, and who may be a good fit.

## A Day in the Life
Walk through a realistic typical workday using specific examples.
Cover morning, midday, afternoon, and end of day.

## Core Knowledge Areas
Key domains and subjects professionals in this field must understand.

## Essential Skills
Cover technical skills, soft skills, and key tools/technologies separately.

## Education and Training Pathways
Cover degrees, alternative paths, certifications, bootcamps,
and realistic time to entry level.

## Career Trajectories and Opportunities
Cover entry, mid, senior titles. Adjacent roles.
Freelance or consulting potential.

## Salary and Compensation
Include entry, mid, senior US salary ranges.
Include salary by city breakdown.
Explain what affects compensation.
Note remote salary impact.

## Industry Outlook and Future Trends
Hiring demand, automation risk, drivers of change,
emerging specializations.

## Interview Prep and Getting Hired
Common interview questions, what employers look for,
portfolio or experience signals that stand out.

## Getting Started — Your 30/60/90 Day Plan
Concrete action steps for the first 30, 60, and 90 days.
Include specific resources, communities, and courses.

## Pros and Cons
Honest assessment of the best and hardest parts of this career.

## Related Careers
Brief descriptions of related paths worth exploring.

Formatting rules:
- Use bullets where they improve readability
- Short paragraphs
- No filler or repetition
- Polished and publishable
""".strip()


def generate_wiki_page(title: str, description: str) -> str:
    print(f"⚙️  Enriching: {title}")
    enrichment = enrich_career(title, description)
    print(f"📝 Writing wiki: {title}")
    prompt = build_wiki_prompt(title, description, enrichment)
    return call_gemini(prompt)


# ----------------------------
# Pipeline
# ----------------------------

def run_pipeline(data: List[Dict[str, Any]]) -> None:
    total = len(data)
    completed = 0
    failed = 0
    skipped = 0

    print(f"📂 Loaded {total} careers")
    print("🚀 Starting pipeline — safe to leave running overnight!")
    print("✅ Checkpoint active — resumes automatically if stopped\n")

    for index, row in enumerate(data, start=1):
        career_id = row["id"]
        title = row["title"]
        description = row.get("description", "").strip()
        blob_path = f"{BLOB_PREFIX}/{career_id}.md"

        print(f"[{index}/{total}] {title}")

        if blob_exists(blob_path):
            print("⏭️  Skipping — already exists")
            skipped += 1
            continue

        try:
            content = generate_wiki_page(title, description)
            upload_text(blob_path, content)
            completed += 1
            time.sleep(SLEEP_BETWEEN_REQUESTS)

        except Exception as e:
            failed += 1
            print(f"❌ Failed: {title} — {e}")

        if index % PROGRESS_EVERY == 0:
            print(f"\n📊 Progress: {completed} done, {skipped} skipped, {failed} failed")
            print(f"📦 In Azure: {completed + skipped}\n")

    print("\n🏁 Session complete!")
    print(f"✅ Generated: {completed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Failed: {failed}")
    print(f"📦 Total in Azure: {completed + skipped}")


if __name__ == "__main__":
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    run_pipeline(all_data[:300])
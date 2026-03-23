import json

# High paying careers to prioritize
HIGH_PAYING_KEYWORDS = [
    "surgeon", "physician", "doctor", "dentist", "orthodontist",
    "psychiatrist", "anesthesiologist", "lawyer", "attorney", "judge",
    "engineer", "software", "data scientist", "machine learning", "ai ",
    "architect", "pilot", "pharmacist", "nurse practitioner", "physician assistant",
    "financial", "investment", "hedge fund", "actuary", "economist",
    "petroleum", "aerospace", "biomedical", "chemical engineer",
    "it manager", "director", "chief", "executive", "vp ", "vice president",
    "consultant", "analyst", "developer", "devops", "cloud", "cybersecurity",
    "product manager", "project manager", "marketing manager", "sales manager",
    "dentist", "optometrist", "podiatrist", "chiropractor", "therapist",
    "scientist", "researcher", "professor", "dean",
    "construction manager", "logistics", "supply chain",
    "accountant", "auditor", "tax", "underwriter", "broker",
    "electrician", "plumber", "hvac", "contractor"
]

with open("occupation_data.json", "r") as f:
    all_rows = json.load(f)

print(f"📂 Loaded {len(all_rows)} total careers")

# Split into categories
onet_rows = [r for r in all_rows if not r["id"].startswith("career-alt") and not r["id"].startswith("career-bls")]
alt_rows = [r for r in all_rows if r["id"].startswith("career-alt")]
bls_rows = [r for r in all_rows if r["id"].startswith("career-bls")]

# Score each alt title by salary keywords
def salary_score(row):
    title_lower = row["title"].lower()
    return sum(1 for kw in HIGH_PAYING_KEYWORDS if kw in title_lower)

# Sort alternates by salary score — highest paying first
alt_rows_scored = sorted(alt_rows, key=salary_score, reverse=True)

# Build final 4,000
# All 1,016 real O*NET + BLS + best alternates up to 4,000
needed = 4000 - len(onet_rows) - len(bls_rows)
final_rows = onet_rows + bls_rows + alt_rows_scored[:needed]

with open("final_data.json", "w") as f:
    json.dump(final_rows, f, indent=2)

print(f"✅ Final dataset: {len(final_rows)} careers")
print(f"   Real O*NET: {len(onet_rows)}")
print(f"   BLS: {len(bls_rows)}")
print(f"   High-value alternates: {needed}")
print(f"\nTop 10 high-paying careers included:")
for row in alt_rows_scored[:10]:
    print(f"  - {row['title']} (score: {salary_score(row)})")
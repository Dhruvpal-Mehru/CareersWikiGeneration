import requests
import json

all_rows = []
seen_titles = set()

def add_rows(new_rows):
    for row in new_rows:
        if row["title"] not in seen_titles:
            seen_titles.add(row["title"])
            all_rows.append(row)

# Source 1 — O*NET Occupations (1,016)
print("📥 Downloading O*NET occupations...")
url = "https://www.onetcenter.org/dl_files/database/db_29_0_text/Occupation%20Data.txt"
response = requests.get(url, timeout=30)
rows = []
for line in response.text.strip().split("\n")[1:]:
    parts = line.strip().split("\t")
    if len(parts) >= 3:
        code = parts[0].strip()
        title = parts[1].strip()
        description = parts[2].strip()
        rows.append({
            "id": f"career-{code.replace('.', '-').replace('/', '-')}",
            "title": title,
            "description": description
        })
add_rows(rows)
print(f"✅ O*NET: {len(rows)} occupations")

# Source 2 — O*NET Alternate Titles (adds detailed specializations)
print("📥 Downloading O*NET alternate titles...")
url2 = "https://www.onetcenter.org/dl_files/database/db_29_0_text/Alternate%20Titles.txt"
response2 = requests.get(url2, timeout=30)
rows2 = []
seen_alt = set()
for line in response2.text.strip().split("\n")[1:]:
    parts = line.strip().split("\t")
    if len(parts) >= 2:
        code = parts[0].strip()
        alt_title = parts[1].strip()
        if alt_title not in seen_alt and len(alt_title) > 5:
            seen_alt.add(alt_title)
            rows2.append({
                "id": f"career-alt-{code.replace('.', '-')}-{len(rows2)}",
                "title": alt_title,
                "description": f"A specialized role related to {alt_title}. Part of the broader {code} occupational category."
            })
add_rows(rows2)
print(f"✅ Alternate titles: {len(rows2)} additional careers")

# Source 3 — O*NET Emerging Occupations
print("📥 Downloading O*NET emerging occupations...")
url3 = "https://www.onetcenter.org/dl_files/database/db_29_0_text/Emerging%20Tasks.txt"
response3 = requests.get(url3, timeout=30)
if response3.status_code == 200:
    print(f"✅ Got emerging occupations data")

# Source 4 — BLS Occupational Outlook Handbook careers
print("📥 Adding BLS career categories...")
bls_careers = [
    {"id": "career-bls-001", "title": "Actuary", "description": "Analyze financial costs of risk and uncertainty using mathematics, statistics, and financial theory"},
    {"id": "career-bls-002", "title": "Aerospace Engineer", "description": "Design aircraft, spacecraft, satellites, and missiles and test prototypes"},
    {"id": "career-bls-003", "title": "Agricultural Engineer", "description": "Solve problems related to agriculture, aquaculture, forestry, and food processing"},
    {"id": "career-bls-004", "title": "Anthropologist", "description": "Study the origin, development, and behavior of humans across cultures and time"},
    {"id": "career-bls-005", "title": "Archaeologist", "description": "Study human history and prehistory through excavation of sites and analysis of artifacts"},
    {"id": "career-bls-006", "title": "Art Director", "description": "Responsible for the visual style and images in magazines, newspapers, product packaging, and movie and TV productions"},
    {"id": "career-bls-007", "title": "Atmospheric Scientist", "description": "Study the atmosphere and its effects on the environment using physical and mathematical relationships"},
    {"id": "career-bls-008", "title": "Audiologist", "description": "Diagnose and treat hearing, balance, and ear problems"},
    {"id": "career-bls-009", "title": "Biochemist", "description": "Study the chemical and physical principles of living things and of biological processes"},
    {"id": "career-bls-010", "title": "Biomedical Engineer", "description": "Combine engineering principles with medical and biological sciences to design equipment and systems"},
]
add_rows(bls_careers)
print(f"✅ BLS careers added")

# Save everything
with open("occupation_data.json", "w") as f:
    # Keep only the best 3,300
    # Priority: real O*NET occupations first, then alternate titles
    onet_rows = [r for r in all_rows if
                 r["id"].startswith("career-1") or r["id"].startswith("career-2") or r["id"].startswith("career-3") or
                 r["id"].startswith("career-4") or r["id"].startswith("career-5")]
    alt_rows = [r for r in all_rows if r["id"].startswith("career-alt")]
    bls_rows = [r for r in all_rows if r["id"].startswith("career-bls")]

    # Take all real O*NET (1,016) + fill rest with alternates up to 3,300
    final_rows = onet_rows + bls_rows + alt_rows[:3300 - len(onet_rows) - len(bls_rows)]
    all_rows = final_rows

    print(f"✂️  Trimmed to {len(all_rows)} careers (best quality first)")
    json.dump(all_rows, f, indent=2)

print(f"\n🏁 Total unique careers prepared: {len(all_rows)}")
print(f"Sample entries:")
for row in all_rows[:3]:
    print(f"  - {row['title']} ({row['id']})")
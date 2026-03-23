import json
import requests

# Try NCES direct CSV
print("Trying NCES CIP data...")
url = "https://nces.ed.gov/ipeds/cipcode/resources/CIPCode2020.csv"
response = requests.get(url, timeout=30)

if response.status_code == 200:
    print(f"✅ Got CSV data!")
    print(response.text[:500])
else:
    print(f"❌ Failed: {response.status_code}")

    # Fallback — use O*NET occupations list
    print("\nTrying O*NET occupations...")
    url2 = "https://www.onetcenter.org/dl_files/database/db_29_0_text/Occupation%20Data.txt"
    response2 = requests.get(url2, timeout=30)
    if response2.status_code == 200:
        print(f"✅ Got O*NET data!")
        print(response2.text[:500])
    else:
        print(f"❌ Failed: {response2.status_code}")
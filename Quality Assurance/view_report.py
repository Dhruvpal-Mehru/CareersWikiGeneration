import json
import glob

# Find the most recent report
reports = glob.glob("quality_report_*.json")
latest = sorted(reports)[-1]

with open(latest) as f:
    report = json.load(f)

print(f"\n{'='*50}")
print(f"Quality Review Report")
print(f"{'='*50}")
print(f"Total reviewed: {report['total_reviewed']}")
print(f"✅ Passed:      {report['total_passed']}")
print(f"🔧 Fixed:       {report['total_fixed']}")
print(f"❌ Failed:      {report['total_failed']}")

if report["issues"]:
    print(f"\nPages with issues:")
    for item in report["issues"]:
        print(f"\n  {item['title']}")
        for issue in item["issues"]:
            print(f"    - [{issue['type']}] {issue['description']}")
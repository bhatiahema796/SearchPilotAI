
import json

from shared.evidence_service import (
    save_crawl_evidence,
    get_project_evidence
)

PROJECT_ID = "SP-A8C3EA533C"

with open(
    "reports/crawler_test.json",
    "r",
    encoding="utf-8"
) as file:
    crawl_data = json.load(file)

saved_count = save_crawl_evidence(
    PROJECT_ID,
    crawl_data
)

evidence = get_project_evidence(PROJECT_ID)

print("\nEVIDENCE SAVED SUCCESSFULLY")
print("=" * 40)

print("Project ID:", PROJECT_ID)
print("New evidence records:", saved_count)
print("Total saved evidence records:", len(evidence))

print("\nSAMPLE EVIDENCE")

for item in evidence[:10]:
    print(
        item["evidence_type"],
        "|",
        item["source_status"],
        "|",
        item["page_url"]
    )

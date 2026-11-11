
from shared.website_crawler import collect_website_data
import json

website = "https://mimosa.cafe/"

result = collect_website_data(website)

print(json.dumps(result, indent=4, ensure_ascii=False))

with open("reports/crawler_test.json", "w", encoding="utf-8") as file:
    json.dump(result, file, indent=4, ensure_ascii=False)

print("\nCrawler test completed.")

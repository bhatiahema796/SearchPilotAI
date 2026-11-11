
from database.db import initialize_database
from shared.project_service import create_project, get_project

# Step 1: Initialize database
initialize_database()

# Step 2: Create test client project
result = create_project(
    company_name="Mimosa Cafe",
    website_url="https://mimosa.cafe/",
    email="test@example.com",
    category="Cafe",
    country="Latvia",
    audience="Local customers",
    services="Coffee and cafe services",
    seo_goals="Improve local SEO and website visibility",
    competitors=[]
)

# Step 3: Display project details
print("\nPROJECT CREATED")
print("=" * 40)
print("Project ID:", result["project_id"])
print("Company:", result["company_name"])
print("Website:", result["website_url"])
print("Status:", result["status"])

# Step 4: Display tasks
print("\nEMPLOYEE TASKS")
for task in result["tasks"]:
    print(task["employee"], "|", task["status"])

# Step 5: Verify database records
saved = get_project(result["project_id"])

print("\nDATABASE VERIFICATION")
print("Project exists:", saved is not None)
print("Saved task count:", len(saved["tasks"]))


import json
import shutil
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from shared.project_service import create_project

BASE_DIR = Path(__file__).resolve().parent.parent
TASK_FILE = BASE_DIR / "data" / "tasks.json"
HISTORY_DIR = BASE_DIR / "data" / "task_history"

EMPLOYEE_TASKS = [
    {
        "employee": "keyword-researcher",
        "task": "Research SEO keywords"
    },
    {
        "employee": "seo-content-writer",
        "task": "Prepare an SEO content plan"
    },
    {
        "employee": "technical-seo-auditor",
        "task": "Review technical SEO opportunities"
    },
    {
        "employee": "aeo-specialist",
        "task": "Identify answer engine optimization opportunities"
    },
    {
        "employee": "competitor-analyst",
        "task": "Identify competitors and content gaps"
    },
    {
        "employee": "performance-analyst",
        "task": "Define SEO and AEO performance metrics"
    },
    {
        "employee": "quality-auditor",
        "task": "Review and verify all six specialist reports"
    }
]


def assign_tasks(business_name, website):

    if not business_name.strip():
        raise ValueError("Business name is required.")

    if not website.strip():
        raise ValueError("Website URL is required.")

    timestamp = datetime.now().astimezone()
    timestamp_text = timestamp.isoformat(timespec="seconds")

    # Archive previous JSON task records.
    if TASK_FILE.exists():
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)

        history_file = HISTORY_DIR / (
            f"tasks_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        )

        if history_file.exists():
            history_file = HISTORY_DIR / (
                f"tasks_{timestamp.strftime('%Y%m%d_%H%M%S')}_"
                f"{uuid4().hex[:6]}.json"
            )

        shutil.copy2(TASK_FILE, history_file)
        print(f"Previous task records archived: {history_file.name}")

    # Create the project and its seven official tasks in SQLite.
    project = create_project(
        company_name=business_name,
        website_url=website
    )

    project_id = project["project_id"]

    # Match SQLite task IDs with employee names.
    database_tasks = {
        item["employee"]: item
        for item in project["tasks"]
    }

    tasks = []

    for item in EMPLOYEE_TASKS:
        employee = item["employee"]
        database_task = database_tasks[employee]

        task = {
            "task_id": database_task["task_id"],
            "project_id": project_id,
            "employee": employee,
            "task": (
                f"{item['task']} for {business_name}"
            ),
            "input": website,
            "assigned_by": "project-manager",
            "created_at": timestamp_text,
            "output": None,
            "report_file": None,
            "verification_report": None,
            "verification_status": "Not Started",
            "status": database_task["status"]
        }

        tasks.append(task)

    TASK_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(TASK_FILE, "w", encoding="utf-8") as file:
        json.dump(tasks, file, indent=4, ensure_ascii=False)

    print("\nPROJECT CREATED SUCCESSFULLY")
    print("=" * 45)
    print("Project ID:", project_id)
    print("Business:", business_name)
    print("Website:", website)
    print("\nProject Manager assigned 7 employees.")

    for task in tasks:
        print(
            f"{task['employee']}: {task['status']} "
            f"| Task ID: {task['task_id']}"
        )

    print("\nSQLite and tasks.json are now connected.")

    return tasks


import json
import shutil
from pathlib import Path
from datetime import datetime
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent.parent
TASK_FILE = BASE_DIR / "data" / "tasks.json"
HISTORY_DIR = BASE_DIR / "data" / "task_history"


def assign_tasks(business_name, website):

    if not business_name.strip():
        raise ValueError("Business name is required.")

    if not website.strip():
        raise ValueError("Website URL is required.")

    timestamp = datetime.now().astimezone()
    timestamp_text = timestamp.isoformat(timespec="seconds")

    # Preserve the previous task records before starting a new run.
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

    tasks = [
        {
            "employee": "keyword-researcher",
            "task": f"Research SEO keywords for {business_name}",
            "input": website
        },
        {
            "employee": "seo-content-writer",
            "task": f"Prepare an SEO content plan for {business_name}",
            "input": website
        },
        {
            "employee": "technical-seo-auditor",
            "task": f"Review technical SEO opportunities for {business_name}",
            "input": website
        },
        {
            "employee": "aeo-specialist",
            "task": f"Identify answer engine optimization opportunities for {business_name}",
            "input": website
        },
        {
            "employee": "competitor-analyst",
            "task": f"Identify competitors and content gaps for {business_name}",
            "input": website
        },
        {
            "employee": "performance-analyst",
            "task": f"Define SEO and AEO performance metrics for {business_name}",
            "input": website
        },
        {
            "employee": "quality-auditor",
            "task": f"Review and verify all six specialist reports for {business_name}",
            "input": website
        }
    ]

    for task in tasks:
        task["task_id"] = str(uuid4())
        task["assigned_by"] = "project-manager"
        task["created_at"] = timestamp_text
        task["output"] = None
        task["report_file"] = None
        task["verification_report"] = None
        task["verification_status"] = "Not Started"

        if task["employee"] == "quality-auditor":
            # The auditor is handled by the verification workflow.
            task["status"] = "Assigned"
        else:
            task["status"] = "Pending"

    TASK_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(TASK_FILE, "w", encoding="utf-8") as file:
        json.dump(tasks, file, indent=4, ensure_ascii=False)

    print("\nProject Manager assigned 7 specialist employees.")

    for task in tasks:
        print(f"{task['employee']}: {task['status']}")

    print("\nQuality Auditor will review all six specialist reports.")

    return tasks

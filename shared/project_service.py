
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from database.db import get_db


BASE_DIR = Path(__file__).resolve().parent.parent
TASK_FILE = BASE_DIR / "data" / "tasks.json"


EMPLOYEE_TASKS = {
    "keyword-researcher": "Research SEO keywords",
    "seo-content-writer": "Prepare an SEO content plan",
    "technical-seo-auditor": "Review technical SEO opportunities",
    "aeo-specialist": "Identify answer engine optimization opportunities",
    "competitor-analyst": "Identify competitors and content gaps",
    "performance-analyst": "Define SEO and AEO performance metrics",
    "quality-auditor": "Review and verify all six specialist reports"
}

EMPLOYEES = list(EMPLOYEE_TASKS.keys())


def current_time():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_project(
    company_name,
    website_url,
    email=None,
    category=None,
    country=None,
    audience=None,
    services=None,
    seo_goals=None,
    competitors=None
):
    if not company_name or not company_name.strip():
        raise ValueError("Company name is required.")

    if not website_url or not website_url.strip():
        raise ValueError("Website URL is required.")

    project_id = "SP-" + uuid.uuid4().hex[:10].upper()
    timestamp = current_time()

    tasks_created = []

    with get_db() as db:

        cursor = db.execute("""
            INSERT INTO clients (
                company_name,
                email,
                created_at
            )
            VALUES (?, ?, ?)
        """, (
            company_name.strip(),
            email.strip() if email else None,
            timestamp
        ))

        client_id = cursor.lastrowid

        db.execute("""
            INSERT INTO projects (
                project_id,
                client_id,
                website_url,
                category,
                country,
                audience,
                services,
                seo_goals,
                competitors,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            client_id,
            website_url.strip(),
            category,
            country,
            audience,
            services,
            seo_goals,
            json.dumps(competitors or []),
            "New Project",
            timestamp,
            timestamp
        ))

        task_input = json.dumps({
            "company_name": company_name.strip(),
            "website_url": website_url.strip(),
            "category": category,
            "country": country,
            "audience": audience,
            "services": services,
            "seo_goals": seo_goals,
            "competitors": competitors or []
        })

        for employee, description in EMPLOYEE_TASKS.items():

            task_id = "TASK-" + uuid.uuid4().hex[:10].upper()

            task_status = (
                "Assigned"
                if employee == "quality-auditor"
                else "Pending"
            )

            db.execute("""
                INSERT INTO tasks (
                    task_id,
                    project_id,
                    employee,
                    description,
                    input_data,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                project_id,
                employee,
                description,
                task_input,
                task_status,
                timestamp
            ))

            tasks_created.append({
                "task_id": task_id,
                "employee": employee,
                "status": task_status
            })

        db.execute("""
            INSERT INTO activity_logs (
                project_id,
                agent_name,
                task_performed,
                output_status,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            project_id,
            "project-manager",
            f"Created project for {company_name}",
            "Completed",
            timestamp
        ))

    return {
        "project_id": project_id,
        "company_name": company_name.strip(),
        "website_url": website_url.strip(),
        "status": "New Project",
        "tasks": tasks_created
    }


def get_project(project_id):

    with get_db() as db:

        project = db.execute("""
            SELECT
                p.*,
                c.company_name,
                c.email
            FROM projects p
            JOIN clients c
                ON c.id = p.client_id
            WHERE p.project_id = ?
        """, (project_id,)).fetchone()

        if not project:
            return None

        tasks = db.execute("""
            SELECT *
            FROM tasks
            WHERE project_id = ?
            ORDER BY created_at
        """, (project_id,)).fetchall()

        return {
            "project": dict(project),
            "tasks": [dict(task) for task in tasks]
        }


def get_all_projects():

    with get_db() as db:

        projects = db.execute("""
            SELECT
                p.*,
                c.company_name,
                c.email
            FROM projects p
            JOIN clients c
                ON c.id = p.client_id
            ORDER BY p.created_at DESC
        """).fetchall()

        return [dict(project) for project in projects]


def sync_project_tasks_to_json(project_id):
    """
    Adds one project's database tasks to tasks.json.
    Existing projects and their task records are preserved.
    """

    project_data = get_project(project_id)

    if not project_data:
        raise ValueError(f"Project not found: {project_id}")

    project = project_data["project"]
    database_tasks = project_data["tasks"]

    TASK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if TASK_FILE.exists():
        try:
            with open(TASK_FILE, "r", encoding="utf-8") as file:
                all_tasks = json.load(file)

            if not isinstance(all_tasks, list):
                all_tasks = []

        except (json.JSONDecodeError, OSError):
            raise ValueError(
                "Could not read tasks.json. "
                "Existing task data was not modified."
            )
    else:
        all_tasks = []

    existing_ids = {
        task.get("task_id")
        for task in all_tasks
        if isinstance(task, dict)
    }

    added_count = 0

    for database_task in database_tasks:

        task_id = database_task["task_id"]

        if task_id in existing_ids:
            continue

        employee = database_task["employee"]

        task_record = {
            "task_id": task_id,
            "project_id": project_id,
            "employee": employee,
            "task": EMPLOYEE_TASKS.get(
                employee,
                database_task["description"]
            ),
            "input": project["website_url"],
            "assigned_by": "project-manager",
            "created_at": database_task["created_at"],
            "output": None,
            "report_file": str(
                Path("reports")
                / project_id
                / f"{employee}.md"
            ).replace("\\", "/"),
            "verification_report": None,
            "verification_status": "Not Started",
            "status": database_task["status"]
        }

        all_tasks.append(task_record)
        existing_ids.add(task_id)
        added_count += 1

    temporary_file = TASK_FILE.with_suffix(".tmp")

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            all_tasks,
            file,
            indent=4,
            ensure_ascii=False
        )

    temporary_file.replace(TASK_FILE)

    return {
        "project_id": project_id,
        "tasks_added": added_count,
        "total_tasks": len(database_tasks)
    }

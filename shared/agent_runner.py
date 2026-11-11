
import json
import re
from pathlib import Path
from datetime import datetime

from shared.ai_engine import ask_ai
from shared.evidence_service import get_project_evidence
from shared.project_service import get_project
from database.db import get_db


BASE_DIR = Path(__file__).resolve().parent.parent

TASK_FILE = BASE_DIR / "data" / "tasks.json"
LOG_FILE = BASE_DIR / "logs" / "task_logs.json"
EMPLOYEE_DIR = BASE_DIR / "employees"
REPORT_DIR = BASE_DIR / "reports"

MAX_REVISION_ATTEMPTS = 2


# --------------------------------------------------
# BASIC HELPERS
# --------------------------------------------------

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def load_json(path, default=None):
    if not path.exists():
        return default if default is not None else []

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def safe_text(value):
    """Convert supported values into safe text."""

    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2
        )

    return str(value)


def validate_ai_response(response, employee, response_type="report"):
    """Reject empty or invalid AI responses."""

    if response is None:
        raise RuntimeError(
            f"AI returned None for {employee} ({response_type})."
        )

    if isinstance(response, (dict, list)):
        response = json.dumps(
            response,
            ensure_ascii=False,
            indent=2
        )

    if not isinstance(response, str):
        raise RuntimeError(
            f"Invalid AI response type for {employee}: "
            f"{type(response).__name__}"
        )

    if not response.strip():
        raise RuntimeError(
            f"AI returned an empty {response_type} for {employee}."
        )

    return response.strip()


# --------------------------------------------------
# SQLITE TASK SYNCHRONIZATION
# --------------------------------------------------

def update_task_record(task):

    task_id = task.get("task_id")

    if not task_id:
        print("DATABASE WARNING: Task ID missing.")
        return

    status = task.get("status", "Pending")

    status_mapping = {
        "Submitted for Review": "Under Review"
    }

    database_status = status_mapping.get(status, status)

    evidence_data = {
        "report_file": task.get("report_file"),
        "verification_status": task.get("verification_status"),
        "verification_report": task.get("verification_report"),
        "revision_attempts": task.get("revision_attempts", 0)
    }

    output_value = safe_text(task.get("output"))

    error_value = safe_text(task.get("error"))

    now = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    started = status == "In Progress"

    terminal_statuses = {
        "Completed",
        "Rejected",
        "Needs Revision",
        "Failed"
    }

    completed = status in terminal_statuses

    try:
        with get_db() as db:

            db.execute(
                """
                UPDATE tasks
                SET
                    status = ?,
                    output = ?,
                    evidence = ?,
                    error = ?,
                    started_at = CASE
                        WHEN ? = 1
                        THEN COALESCE(started_at, ?)
                        ELSE started_at
                    END,
                    completed_at = CASE
                        WHEN ? = 1 THEN ?
                        ELSE completed_at
                    END
                WHERE task_id = ?
                """,
                (
                    database_status,
                    output_value,
                    json.dumps(
                        evidence_data,
                        ensure_ascii=False
                    ),
                    error_value,
                    1 if started else 0,
                    now,
                    1 if completed else 0,
                    now,
                    task_id
                )
            )

        print(
            f"DATABASE TASK UPDATED: "
            f"{task.get('employee')} - {database_status}"
        )

    except Exception as error:
        print(f"DATABASE TASK WARNING: {error}")


# --------------------------------------------------
# ACTIVITY LOGGING
# --------------------------------------------------

def save_log(agent, task, status, project_id=None):

    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    task_text = safe_text(task)
    status_text = safe_text(status)

    log_entry = {
        "timestamp": timestamp,
        "agent_name": agent,
        "task_performed": task_text,
        "output_status": status_text
    }

    logs = load_json(LOG_FILE, [])

    logs.append(log_entry)
    save_json(LOG_FILE, logs)

    print(f"LOCAL LOG SAVED: {agent} - {status_text}")

    if project_id:

        try:
            with get_db() as db:

                db.execute(
                    """
                    INSERT INTO activity_logs (
                        project_id,
                        agent_name,
                        task_performed,
                        output_status,
                        timestamp
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        agent,
                        task_text,
                        status_text,
                        timestamp
                    )
                )

        except Exception as error:
            print(f"SQLITE LOG WARNING: {error}")

    try:
        from integrations.google_sheets import log_activity

        log_activity(
            timestamp,
            agent,
            task_text,
            status_text
        )

    except Exception as error:
        print(f"GOOGLE SHEETS WARNING: {error}")
        print("Local log is safe.")


# --------------------------------------------------
# EMPLOYEE INSTRUCTIONS
# --------------------------------------------------

def load_instructions(employee):

    instruction_file = (
        EMPLOYEE_DIR / employee / "instructions.md"
    )

    if not instruction_file.exists():
        raise FileNotFoundError(
            f"Instructions missing for {employee}"
        )

    return instruction_file.read_text(
        encoding="utf-8"
    )


# --------------------------------------------------
# PROJECT AND EVIDENCE
# --------------------------------------------------

def get_project_context(project_id):

    if not project_id:
        raise ValueError(
            "Project ID is missing from task."
        )

    project_data = get_project(project_id)

    if not project_data:
        raise ValueError(
            f"Project not found: {project_id}"
        )

    project = project_data["project"]

    evidence_records = get_project_evidence(project_id)

    if not evidence_records:
        raise ValueError(
            f"No website evidence found for {project_id}"
        )

    return project, evidence_records


def format_evidence(evidence_records):

    evidence_lines = []

    for record in evidence_records:

        evidence_lines.append(
            f"""
Page URL: {record.get('page_url')}
Evidence Type: {record.get('evidence_type')}
Source Status: {record.get('source_status')}
Collected Value: {record.get('evidence_value')}
Collected At: {record.get('collected_at')}
"""
        )

    return "\n".join(evidence_lines)


def format_project_details(project):

    return f"""
Company Name: {project.get('company_name')}
Website: {project.get('website_url')}
Category: {project.get('category') or 'Not Provided'}
Country: {project.get('country') or 'Not Provided'}
Target Audience: {project.get('audience') or 'Not Provided'}
Services: {project.get('services') or 'Not Provided'}
SEO Goals: {project.get('seo_goals') or 'Not Provided'}
Competitors: {project.get('competitors') or 'Not Provided'}
"""


# --------------------------------------------------
# QUALITY AUDITOR TASK
# --------------------------------------------------

def update_auditor_task(tasks, status, message):

    auditor_task = next(
        (
            task for task in tasks
            if task["employee"] == "quality-auditor"
        ),
        None
    )

    if auditor_task is None:
        print("Quality Auditor task not found.")
        return

    auditor_task["status"] = status
    auditor_task["output"] = message

    auditor_task["updated_at"] = (
        datetime.now().astimezone().isoformat(
            timespec="seconds"
        )
    )

    update_task_record(auditor_task)
    save_json(TASK_FILE, tasks)


# --------------------------------------------------
# GENERATE EMPLOYEE REPORT
# --------------------------------------------------

def generate_report(
    employee,
    task,
    instructions,
    previous_report=None,
    feedback=None
):

    current_date = datetime.now().astimezone().date().isoformat()

    project_id = task.get("project_id")

    project, evidence_records = get_project_context(
        project_id
    )

    evidence_context = format_evidence(
        evidence_records
    )

    project_context = format_project_details(
        project
    )

    revision_context = ""

    if previous_report and feedback:

        revision_context = f"""
PREVIOUS REPORT:
{previous_report}

QUALITY AUDITOR FEEDBACK:
{feedback}

REVISION INSTRUCTIONS:
- Correct specific issues identified.
- Preserve valid evidence.
- Never invent evidence.
- Explain limitations honestly.
- Return the complete revised report.
"""

    prompt = f"""
You are working as {employee} at SearchPilot AI.

EMPLOYEE INSTRUCTIONS:
{instructions}

CLIENT PROJECT DETAILS:
{project_context}

PROJECT ID:
{project_id}

ASSIGNED TASK:
{task['task']}

WEBSITE EVIDENCE:
{evidence_context}

CURRENT DATE:
{current_date}

STRICT EVIDENCE RULES:

1. Use project-specific evidence only.
2. Do not invent keyword search volumes.
3. Do not invent rankings, traffic or backlinks.
4. Do not invent competitor findings.
5. Do not claim Analytics or Search Console access
   without actual authorized data.
6. Do not invent page speed or Core Web Vitals results.
7. Separate Observed Findings, Recommendations
   and Not Tested / Data Unavailable.
8. Missing headings in static HTML do not prove
   that rendered pages have no headings.
9. Every website-specific observation must be
   traceable to supplied evidence.
10. Never describe recommendations as completed fixes.
11. Use the actual client and website.
12. Never use fictional Glow Nest data.
13. Do not use unresolved placeholders.
14. Clearly identify assumptions.
15. Explain insufficient evidence honestly.

REPORT REQUIREMENTS:

- Employee name and client details.
- Project ID and website.
- Executive summary.
- Relevant findings for the assigned role.
- Evidence and source URLs.
- Limitations.
- Prioritized recommendations.
- Professional Markdown.
- Current date.

{revision_context}
"""

    response = ask_ai(
        prompt,
        system_prompt=(
            f"You are the {employee} specialist at SearchPilot AI. "
            "Use project-specific evidence only. "
            "Be accurate, transparent and evidence-conscious. "
            "Never fabricate observations or test results."
        )
    )

    return validate_ai_response(
        response,
        employee,
        "report"
    )


# --------------------------------------------------
# INDEPENDENT QUALITY VERIFICATION
# --------------------------------------------------

def verify_report(
    employee,
    task_description,
    report,
    project_id
):

    auditor_instructions = load_instructions(
        "quality-auditor"
    )

    project, evidence_records = get_project_context(
        project_id
    )

    evidence_context = format_evidence(
        evidence_records
    )

    project_context = format_project_details(
        project
    )

    prompt = f"""
You are the independent Quality Auditor
of SearchPilot AI.

QUALITY AUDITOR INSTRUCTIONS:
{auditor_instructions}

CLIENT PROJECT:
{project_context}

PROJECT ID:
{project_id}

EMPLOYEE:
{employee}

ASSIGNED TASK:
{task_description}

INDEPENDENT WEBSITE EVIDENCE:
{evidence_context}

REPORT TO REVIEW:
{report}

CHECK:

1. Correct project and client.
2. Evidence-backed website findings.
3. Correct source URLs.
4. Unsupported or invented claims.
5. Invented keyword volumes or rankings.
6. Unsupported competitor information.
7. False claims of tests performed.
8. Missing sections or placeholders.
9. Clearly labelled assumptions.
10. Recommendations distinguished from findings.
11. Untested issues incorrectly assigned severity.
12. Completion of assigned task.

STRICT RULES:

- Never approve fabricated findings.
- Reject false claims of completed tests.
- Do not approve evidence from another project.
- Do not approve invented traffic or ranking figures.
- Do not reject honest limitations simply because
  external data is unavailable.
- Approve only when factual claims are supported
  or clearly qualified.

DECISION GUIDANCE:

APPROVED:
The report fulfils the task and is evidence-supported.

NEEDS REVISION:
Correctable issues or missing sections exist.

REJECTED:
Serious fabrication or fundamental project mismatch.

Return exactly one first decision line:

DECISION: APPROVED

DECISION: NEEDS REVISION

DECISION: REJECTED

REASONS:
List specific findings.

CORRECTIONS:
List corrections, or write None.

FINAL REVIEW:
Explain the decision.
"""

    review = ask_ai(
        prompt,
        system_prompt=(
            "You are a strict independent Quality Auditor. "
            "Compare the report against the original "
            "project evidence. Never approve fabrication."
        )
    )

    review = validate_ai_response(
        review,
        "quality-auditor",
        "review"
    )

    match = re.search(
        r"(?im)^\s*DECISION:\s*"
        r"(APPROVED|NEEDS REVISION|REJECTED)\s*$",
        review
    )

    if not match:
        return (
            "Invalid Review",
            "Needs Revision",
            review
        )

    decision = match.group(1).title()

    if decision == "Approved":
        status = "Completed"
    elif decision == "Rejected":
        status = "Rejected"
    else:
        status = "Needs Revision"

    return decision, status, review


# --------------------------------------------------
# EXECUTION WORKFLOW
# --------------------------------------------------

def execute_pending_tasks():

    if not TASK_FILE.exists():
        print("No task file found.")
        return

    tasks = load_json(TASK_FILE, [])

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    pending_specialists = [
        task for task in tasks
        if task.get("status") == "Pending"
        and task.get("employee") != "quality-auditor"
    ]

    if not pending_specialists:
        print("No pending specialist tasks found.")
        return

    auditor_task = next(
        (
            task for task in tasks
            if task["employee"] == "quality-auditor"
        ),
        None
    )

    project_id = (
        pending_specialists[0].get("project_id")
    )

    if auditor_task:

        auditor_task["status"] = "In Progress"
        auditor_task["output"] = (
            "Independent review process started."
        )

        update_task_record(auditor_task)
        save_json(TASK_FILE, tasks)

        save_log(
            "quality-auditor",
            "Started specialist report review process",
            "In Progress",
            project_id
        )

    review_attempts = 0
    approved_count = 0
    revision_count = 0
    rejected_count = 0
    failed_count = 0

    unique_reports_reviewed = set()

    try:

        for task in tasks:

            if task.get("status") != "Pending":
                continue

            employee = task["employee"]

            if employee == "quality-auditor":
                continue

            project_id = task.get("project_id")

            print(f"\nStarting employee: {employee}")

            try:

                instructions = load_instructions(employee)

                task["status"] = "In Progress"

                update_task_record(task)
                save_json(TASK_FILE, tasks)

                save_log(
                    employee,
                    task["task"],
                    "In Progress",
                    project_id
                )

                report = generate_report(
                    employee,
                    task,
                    instructions
                )

                revision_attempts = 0

                while True:

                    report_file = (
                        REPORT_DIR / f"{employee}.md"
                    )

                    report_file.write_text(
                        report,
                        encoding="utf-8"
                    )

                    task["output"] = report

                    task["report_file"] = str(
                        report_file.relative_to(BASE_DIR)
                    )

                    task["status"] = "Submitted for Review"
                    task["verification_status"] = "Pending"

                    update_task_record(task)
                    save_json(TASK_FILE, tasks)

                    save_log(
                        employee,
                        task["task"],
                        "Submitted for Review",
                        project_id
                    )

                    print(
                        f"Submitted for review: {employee}"
                    )

                    decision, final_status, review = verify_report(
                        employee,
                        task["task"],
                        report,
                        project_id
                    )

                    review_file = (
                        REPORT_DIR / f"{employee}-review.md"
                    )

                    review_file.write_text(
                        review,
                        encoding="utf-8"
                    )

                    task["verification_status"] = decision

                    task["verification_report"] = str(
                        review_file.relative_to(BASE_DIR)
                    )

                    task["revision_attempts"] = revision_attempts

                    review_attempts += 1
                    unique_reports_reviewed.add(employee)

                    update_task_record(task)
                    save_json(TASK_FILE, tasks)

                    save_log(
                        "quality-auditor",
                        f"Reviewed report of {employee}: {decision}",
                        final_status,
                        project_id
                    )

                    print(
                        f"Quality review: "
                        f"{employee} - {final_status}"
                    )

                    if final_status == "Completed":

                        task["status"] = "Completed"
                        approved_count += 1

                        update_task_record(task)
                        save_json(TASK_FILE, tasks)

                        save_log(
                            employee,
                            task["task"],
                            "Completed - Approved",
                            project_id
                        )

                        break

                    if final_status == "Rejected":

                        task["status"] = "Rejected"
                        rejected_count += 1

                        update_task_record(task)
                        save_json(TASK_FILE, tasks)

                        save_log(
                            employee,
                            task["task"],
                            "Rejected",
                            project_id
                        )

                        break

                    if revision_attempts >= MAX_REVISION_ATTEMPTS:

                        task["status"] = "Needs Revision"
                        revision_count += 1

                        update_task_record(task)
                        save_json(TASK_FILE, tasks)

                        save_log(
                            employee,
                            task["task"],
                            "Needs Revision - Maximum attempts reached",
                            project_id
                        )

                        break

                    revision_attempts += 1

                    task["status"] = "In Progress"
                    task["revision_attempts"] = revision_attempts

                    update_task_record(task)
                    save_json(TASK_FILE, tasks)

                    save_log(
                        employee,
                        "Revising report based on Quality Auditor feedback",
                        f"Revision Attempt {revision_attempts}",
                        project_id
                    )

                    report = generate_report(
                        employee,
                        task,
                        instructions,
                        previous_report=report,
                        feedback=review
                    )

            except Exception as error:

                task["status"] = "Failed"
                task["verification_status"] = "Not Verified"
                task["error"] = str(error)

                failed_count += 1

                update_task_record(task)
                save_json(TASK_FILE, tasks)

                save_log(
                    employee,
                    task["task"],
                    f"Failed: {error}",
                    project_id
                )

                print(
                    f"Failed: {employee} - {error}"
                )

        # ------------------------------------------
        # FINAL QUALITY AUDITOR SUMMARY
        # ------------------------------------------

        if auditor_task:

            summary = {
                "reports_reviewed": len(unique_reports_reviewed),
                "review_attempts": review_attempts,
                "approved": approved_count,
                "needs_revision": revision_count,
                "rejected": rejected_count,
                "failed": failed_count
            }

            unfinished = [
                task for task in tasks
                if task.get("employee") != "quality-auditor"
                and task.get("status") in (
                    "Pending",
                    "In Progress",
                    "Submitted for Review"
                )
            ]

            if unfinished:
                auditor_task["status"] = "In Progress"
                auditor_task["verification_status"] = (
                    "Review Process Incomplete"
                )
            else:
                auditor_task["status"] = "Completed"
                auditor_task["verification_status"] = (
                    "Review Process Completed"
                )

            auditor_task["output"] = summary

            auditor_task["updated_at"] = (
                datetime.now().astimezone().isoformat(
                    timespec="seconds"
                )
            )

            update_task_record(auditor_task)
            save_json(TASK_FILE, tasks)

            save_log(
                "quality-auditor",
                "Completed review of specialist reports",
                auditor_task["status"],
                project_id
            )

    except Exception as error:

        if auditor_task:

            auditor_task["status"] = "Failed"
            auditor_task["error"] = str(error)

            update_task_record(auditor_task)
            save_json(TASK_FILE, tasks)

        print(
            f"Quality Auditor process failed: {error}"
        )

    print("\nFINAL TASK STATUS")
    print("=" * 50)

    for task in tasks:

        print(
            f"{task['employee']}: {task['status']} "
            f"| Verification: "
            f"{task.get('verification_status', 'Not Started')}"
        )


if __name__ == "__main__":
    execute_pending_tasks()

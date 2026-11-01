
import json
import re
from pathlib import Path
from datetime import datetime

from shared.ai_engine import ask_ai

BASE_DIR = Path(__file__).resolve().parent.parent

TASK_FILE = BASE_DIR / "data" / "tasks.json"
LOG_FILE = BASE_DIR / "logs" / "task_logs.json"
EMPLOYEE_DIR = BASE_DIR / "employees"
REPORT_DIR = BASE_DIR / "reports"

MAX_REVISION_ATTEMPTS = 2


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def save_log(agent, task, status):
    """Save activity locally and send it to Google Sheets."""

    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    log_entry = {
        "timestamp": timestamp,
        "agent_name": agent,
        "task_performed": task,
        "output_status": status
    }

    # Always save local JSON log first.
    logs = []

    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as file:
            logs = json.load(file)

    logs.append(log_entry)
    save_json(LOG_FILE, logs)

    print(f"LOCAL LOG SAVED: {agent} - {status}")

    # Send activity to Google Sheets.
    try:
        from integrations.google_sheets import log_activity

        log_activity(
            timestamp,
            agent,
            task,
            status
        )

    except Exception as error:
        print(f"GOOGLE SHEETS WARNING: {error}")
        print("Local log is safe. Cloud logging can be retried later.")


def load_instructions(employee):
    instruction_file = EMPLOYEE_DIR / employee / "instructions.md"

    if not instruction_file.exists():
        raise FileNotFoundError(
            f"Instructions missing for {employee}"
        )

    return instruction_file.read_text(encoding="utf-8")


def update_auditor_task(tasks, status, message):
    """Update the official Quality Auditor task record."""

    auditor_task = next(
        (
            task for task in tasks
            if task["employee"] == "quality-auditor"
        ),
        None
    )

    if auditor_task is None:
        print("Warning: Quality Auditor task record not found.")
        return

    auditor_task["status"] = status
    auditor_task["output"] = message
    auditor_task["updated_at"] = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    save_json(TASK_FILE, tasks)


def generate_report(
    employee,
    task,
    instructions,
    previous_report=None,
    feedback=None
):
    current_date = datetime.now().astimezone().date().isoformat()

    is_demo = "example.com" in task["input"].lower()

    revision_context = ""

    if previous_report and feedback:
        revision_context = f"""
PREVIOUS REPORT:
{previous_report}

QUALITY AUDITOR FEEDBACK:
{feedback}

REVISION INSTRUCTIONS:
- Correct the issues identified by the Quality Auditor.
- Preserve useful and valid information.
- Never invent evidence to satisfy the reviewer.
- Explain limitations that cannot be resolved.
- Return the complete revised report.
"""

    prompt = f"""
You are working as {employee} at SearchPilot AI.

EMPLOYEE INSTRUCTIONS:
{instructions}

ASSIGNED TASK:
{task['task']}

BUSINESS:
Glow Nest Candle Studio (Fictional Demo Client)

WEBSITE PROVIDED:
{task['input']}

CURRENT DATE:
{current_date}

DEMO MODE:
{"YES" if is_demo else "NO"}

IMPORTANT RULES:
- Glow Nest Candle Studio is a fictional example business.
- Do not claim that a live client website has been audited.
- No live crawling or external website testing tool is connected.
- Do not claim page speed, indexing, metadata or schema tests
  were performed unless actual evidence is available.
- Mark untested items as "Not Tested".
- Do not assign High, Medium or Low severity to untested issues.
- Separate observed facts, assumptions and recommendations.
- Never invent search volumes, rankings, traffic, competitor
  findings, performance metrics, evidence or sources.
- Use the current date provided above.
- Do not use unresolved placeholders.
- Produce useful, structured and original work.
- Return a professional Markdown report.

{revision_context}
"""

    return ask_ai(
        prompt,
        system_prompt=(
            f"You are the {employee} specialist at SearchPilot AI. "
            "Be accurate, transparent and evidence-conscious."
        )
    )


def verify_report(employee, task_description, report):
    auditor_instructions = load_instructions("quality-auditor")

    prompt = f"""
You are the Quality Auditor of SearchPilot AI.

QUALITY AUDITOR INSTRUCTIONS:
{auditor_instructions}

EMPLOYEE:
{employee}

ORIGINAL ASSIGNED TASK:
{task_description}

REPORT TO REVIEW:
{report}

Review the actual report.

Check:
1. Accuracy and factual reliability.
2. Unsupported or invented claims.
3. Missing information and incomplete sections.
4. Placeholder text.
5. Originality and relevance.
6. Whether the assigned task was fulfilled.
7. Whether assumptions are clearly labelled.
8. Whether the report claims tests that were not performed.

IMPORTANT:
- This is a fictional demo client.
- Do not require real client data that was never supplied.
- Do not reject a transparent demo report merely because
  live website access is unavailable.
- Reject fabricated findings and false claims of testing.
- Recommendations must be distinguished from observations.
- Untested issues must not be assigned severity ratings.
- Approve only when the report meets the quality requirements.

Return your decision using this exact format.
The FIRST decision line must be exactly one of these:

DECISION: APPROVED

DECISION: NEEDS REVISION

DECISION: REJECTED

REASONS:
List specific findings.

CORRECTIONS:
List specific required corrections, or write None.

FINAL REVIEW:
Explain your decision.
"""

    review = ask_ai(
        prompt,
        system_prompt=(
            "You are a strict Quality Auditor. "
            "Never approve unsupported or fabricated findings. "
            "Judge only the evidence and content actually provided."
        )
    )

    match = re.search(
        r"(?im)^\s*DECISION:\s*(APPROVED|NEEDS REVISION|REJECTED)\s*$",
        review
    )

    if not match:
        return "Invalid Review", "Needs Revision", review

    decision = match.group(1).title()

    if decision == "Approved":
        status = "Completed"
    elif decision == "Rejected":
        status = "Rejected"
    else:
        status = "Needs Revision"

    return decision, status, review


def execute_pending_tasks():
    if not TASK_FILE.exists():
        print("No task file found.")
        return

    with open(TASK_FILE, "r", encoding="utf-8") as file:
        tasks = json.load(file)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    auditor_task = next(
        (
            task for task in tasks
            if task["employee"] == "quality-auditor"
        ),
        None
    )

    if auditor_task:
        auditor_task["status"] = "In Progress"
        auditor_task["output"] = "Review process started."

        save_json(TASK_FILE, tasks)

        save_log(
            "quality-auditor",
            "Started specialist report review process",
            "In Progress"
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

            print(f"\nStarting employee: {employee}")

            try:
                instructions = load_instructions(employee)

                task["status"] = "In Progress"
                save_json(TASK_FILE, tasks)

                save_log(
                    employee,
                    task["task"],
                    "In Progress"
                )

                report = generate_report(
                    employee,
                    task,
                    instructions
                )

                revision_attempts = 0

                while True:
                    report_file = REPORT_DIR / f"{employee}.md"

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

                    save_json(TASK_FILE, tasks)

                    save_log(
                        employee,
                        task["task"],
                        "Submitted for Review"
                    )

                    print(f"Submitted for review: {employee}")

                    decision, final_status, review = verify_report(
                        employee,
                        task["task"],
                        report
                    )

                    review_file = REPORT_DIR / f"{employee}-review.md"

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

                    save_json(TASK_FILE, tasks)

                    save_log(
                        "quality-auditor",
                        f"Reviewed report of {employee}: {decision}",
                        final_status
                    )

                    print(
                        f"Quality review: {employee} - {final_status}"
                    )

                    if final_status == "Completed":
                        task["status"] = "Completed"
                        approved_count += 1

                        save_json(TASK_FILE, tasks)

                        save_log(
                            employee,
                            task["task"],
                            "Completed - Approved"
                        )
                        break

                    if final_status == "Rejected":
                        task["status"] = "Rejected"
                        rejected_count += 1

                        save_json(TASK_FILE, tasks)

                        save_log(
                            employee,
                            task["task"],
                            "Rejected"
                        )
                        break

                    if revision_attempts >= MAX_REVISION_ATTEMPTS:
                        task["status"] = "Needs Revision"
                        revision_count += 1

                        save_json(TASK_FILE, tasks)

                        save_log(
                            employee,
                            task["task"],
                            "Needs Revision - Maximum attempts reached"
                        )

                        print(
                            f"Maximum revisions reached for {employee}."
                        )
                        break

                    revision_attempts += 1

                    task["status"] = "In Progress"
                    task["revision_attempts"] = revision_attempts

                    save_json(TASK_FILE, tasks)

                    save_log(
                        employee,
                        "Revising report based on Quality Auditor feedback",
                        f"Revision Attempt {revision_attempts}"
                    )

                    print(
                        f"Sending feedback to {employee}. "
                        f"Attempt {revision_attempts}/"
                        f"{MAX_REVISION_ATTEMPTS}"
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

                save_json(TASK_FILE, tasks)

                save_log(
                    employee,
                    task["task"],
                    f"Failed: {error}"
                )

                print(f"Failed: {employee} - {error}")

        if auditor_task:
            summary = {
                "reports_reviewed": len(unique_reports_reviewed),
                "review_attempts": review_attempts,
                "approved": approved_count,
                "needs_revision": revision_count,
                "rejected": rejected_count,
                "failed": failed_count
            }

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

            save_json(TASK_FILE, tasks)

            save_log(
                "quality-auditor",
                "Completed review of specialist reports",
                "Completed"
            )

    except Exception as error:
        if auditor_task:
            auditor_task["status"] = "Failed"
            auditor_task["error"] = str(error)
            save_json(TASK_FILE, tasks)

        print(f"Quality Auditor process failed: {error}")

    print("\nFINAL TASK STATUS")
    print("=" * 45)

    for task in tasks:
        print(
            f"{task['employee']}: {task['status']} "
            f"| Verification: "
            f"{task.get('verification_status', 'Not Started')}"
        )


if __name__ == "__main__":
    execute_pending_tasks()

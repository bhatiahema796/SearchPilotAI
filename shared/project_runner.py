
import json
from pathlib import Path
from datetime import datetime, timezone

from shared.email_service import send_final_report_email

from shared.project_service import (
    get_project,
    sync_project_tasks_to_json
)

from shared.agent_runner import (
    load_json,
    save_json,
    load_instructions,
    generate_report,
    verify_report,
    update_task_record,
    save_log
)

from shared.website_crawler import collect_website_data

from shared.evidence_service import (
    save_crawl_evidence,
    get_project_evidence
)

from database.db import get_db


BASE_DIR = Path(__file__).resolve().parent.parent
TASK_FILE = BASE_DIR / "data" / "tasks.json"
REPORT_DIR = BASE_DIR / "reports"

MAX_REVISION_ATTEMPTS = 2

REQUIRED_SPECIALISTS = {
    "keyword-researcher",
    "seo-content-writer",
    "technical-seo-auditor",
    "aeo-specialist",
    "competitor-analyst",
    "performance-analyst"
}


def current_time():
    return datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )


def get_project_tasks(project_id):

    tasks = load_json(TASK_FILE, [])

    return [
        task for task in tasks
        if task.get("project_id") == project_id
    ]


def update_project_task(project_task, all_tasks):

    for index, task in enumerate(all_tasks):

        if task.get("task_id") == project_task.get("task_id"):
            all_tasks[index] = project_task
            break

    save_json(TASK_FILE, all_tasks)
    update_task_record(project_task)


def collect_project_evidence(project_id):

    project_data = get_project(project_id)

    if not project_data:
        raise ValueError("Project not found.")

    project = project_data["project"]
    website = project["website_url"]

    existing_evidence = get_project_evidence(project_id)

    if existing_evidence:
        print("Existing website evidence found.")
        print("Skipping duplicate website crawl.")
        return len(existing_evidence)

    print("\nStarting website evidence collection.")
    print(f"Website: {website}")

    crawl_result = collect_website_data(website)

    successful_pages = [
        page for page in crawl_result.get("pages", [])
        if not page.get("error")
    ]

    if not successful_pages:
        raise RuntimeError(
            "Website crawling did not collect a successful page. "
            "Agent execution has been stopped."
        )

    evidence_count = save_crawl_evidence(
        project_id,
        crawl_result
    )

    print(f"Evidence records saved: {evidence_count}")

    for error in crawl_result.get("errors", []):
        print(f"CRAWLER NOTICE: {error}")

    if not evidence_count:
        raise RuntimeError(
            "No website evidence could be collected. "
            "Agent execution has been stopped."
        )

    return evidence_count


def create_final_report(project_id):

    project_data = get_project(project_id)

    if not project_data:
        raise ValueError("Project not found.")

    project = project_data["project"]
    tasks = project_data["tasks"]

    specialist_tasks = [
        task for task in tasks
        if task["employee"] in REQUIRED_SPECIALISTS
    ]

    approved_tasks = []

    for task in specialist_tasks:

        evidence = task.get("evidence") or "{}"

        try:
            evidence_data = json.loads(evidence)
        except (TypeError, json.JSONDecodeError):
            evidence_data = {}

        verification = evidence_data.get(
            "verification_status"
        )

        if (
            task["status"] == "Completed"
            and verification == "Approved"
        ):
            approved_tasks.append(task)

    if len(specialist_tasks) != 6 or len(approved_tasks) != 6:
        raise RuntimeError(
            "Final report blocked: all six specialist "
            "reports have not passed Quality Auditor approval."
        )

    report_folder = REPORT_DIR / project_id
    report_folder.mkdir(parents=True, exist_ok=True)

    final_file = report_folder / "final_report.md"

    sections = [
        "# SearchPilot AI - Final SEO/AEO Report",
        f"\nCompany: {project['company_name']}",
        f"\nWebsite: {project['website_url']}",
        f"\nProject ID: {project_id}",
        f"\nGenerated: {current_time()}",
        "\n\n## Quality Assurance Status",
        "\nAll six specialist reports have been independently approved."
    ]

    for task in approved_tasks:

        employee = task["employee"]

        report_path = report_folder / f"{employee}.md"

        if not report_path.exists():
            raise RuntimeError(
                f"Approved report file missing: {employee}"
            )

        report_content = report_path.read_text(
            encoding="utf-8"
        )

        sections.extend([
            f"\n\n---\n\n## {employee.replace('-', ' ').title()}",
            "\n",
            report_content
        ])

    final_file.write_text(
        "\n".join(sections),
        encoding="utf-8"
    )

    with get_db() as db:

        next_version = db.execute("""
            SELECT COALESCE(MAX(version), 0) + 1
            FROM reports
            WHERE project_id = ?
        """, (project_id,)).fetchone()[0]

        db.execute("""
            INSERT INTO reports (
                project_id,
                version,
                file_path,
                qa_status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            project_id,
            next_version,
            str(final_file.relative_to(BASE_DIR)),
            "Approved",
            current_time()
        ))

        db.execute("""
            UPDATE projects
            SET status = ?, updated_at = ?
            WHERE project_id = ?
        """, (
            "Quality Approved",
            current_time(),
            project_id
        ))

    return final_file


def run_project(project_id):

    print("\n" + "=" * 60)
    print("SEARCHPILOT AI - PROJECT EXECUTION")
    print("=" * 60)

    project_data = get_project(project_id)

    if not project_data:
        raise ValueError(
            f"Project not found: {project_id}"
        )

    project = project_data["project"]

    print(f"Client: {project['company_name']}")
    print(f"Project ID: {project_id}")

    # Step 1: Collect website evidence
    collect_project_evidence(project_id)

    # Step 2: Synchronize project tasks
    sync_result = sync_project_tasks_to_json(project_id)

    print(
        f"Tasks synchronized: {sync_result['tasks_added']}"
    )

    all_tasks = load_json(TASK_FILE, [])

    project_tasks = [
        task for task in all_tasks
        if task.get("project_id") == project_id
    ]

    auditor_task = next(
        (
            task for task in project_tasks
            if task["employee"] == "quality-auditor"
        ),
        None
    )

    specialist_tasks = [
        task for task in project_tasks
        if task["employee"] in REQUIRED_SPECIALISTS
    ]

    if len(specialist_tasks) != 6:
        raise RuntimeError(
            "Exactly six specialist tasks are required."
        )

    if not auditor_task:
        raise RuntimeError(
            "Quality Auditor task not found."
        )

    approved_count = 0
    rejected_count = 0
    revision_count = 0
    failed_count = 0
    review_attempts = 0

    # Step 3: Execute specialists
    for task in specialist_tasks:

        # Skip specialists that are already approved.
        if (
            task.get("status") == "Completed"
            and task.get("verification_status") == "Approved"
        ):
            print(
                f"Skipping already approved: {task['employee']}"
            )
            approved_count += 1
            continue

        # Rejected and Failed tasks are not automatically rerun.
        if task.get("status") in (
            "Rejected",
            "Failed"
        ):
            print(
                f"Skipping terminal task: {task['employee']} "
                f"({task['status']})"
            )

            if task["status"] == "Rejected":
                rejected_count += 1
            else:
                failed_count += 1

            continue

        employee = task["employee"]

        # Retrieve the old report and QA feedback before changing
        # the task status from Needs Revision.
        previous_report = None
        feedback = None

        if task.get("status") == "Needs Revision":

            print(
                f"\nPreparing revision for: {employee}"
            )

            previous_report = task.get("output")

            if not isinstance(previous_report, str) or not previous_report.strip():

                report_path = task.get("report_file")

                if report_path:
                    full_path = BASE_DIR / report_path

                    if full_path.exists():
                        previous_report = full_path.read_text(
                            encoding="utf-8"
                        )

            review_path = task.get("verification_report")

            if review_path:
                full_review_path = BASE_DIR / review_path

                if full_review_path.exists():
                    feedback = full_review_path.read_text(
                        encoding="utf-8"
                    )

            # Do not overwrite or rerun if previous evidence is missing.
            if not previous_report or not feedback:

                print(
                    f"Cannot revise {employee}: "
                    "previous report or QA feedback is missing."
                )

                revision_count += 1
                continue

        print(f"\nStarting employee: {employee}")

        try:

            instructions = load_instructions(employee)

            task["status"] = "In Progress"
            update_project_task(task, all_tasks)

            save_log(
                employee,
                task["task"],
                "In Progress",
                project_id
            )

            # For a Needs Revision task, use its old report and
            # auditor feedback. New tasks start without either.
            report = generate_report(
                employee,
                task,
                instructions,
                previous_report=previous_report,
                feedback=feedback
            )

            # This is a new revision cycle for the current task.
            revision_attempts = 0

            while True:

                report_folder = REPORT_DIR / project_id
                report_folder.mkdir(
                    parents=True,
                    exist_ok=True
                )

                report_file = report_folder / f"{employee}.md"

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

                update_project_task(task, all_tasks)

                save_log(
                    employee,
                    task["task"],
                    "Submitted for Review",
                    project_id
                )

                # Independent Quality Auditor verification
                decision, final_status, review = verify_report(
                    employee,
                    task["task"],
                    report,
                    project_id
                )

                review_file = (
                    report_folder / f"{employee}-review.md"
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

                print(
                    f"Quality review: {employee} - {decision}"
                )

                if decision == "Approved":

                    task["status"] = "Completed"
                    approved_count += 1

                    update_project_task(task, all_tasks)

                    save_log(
                        employee,
                        task["task"],
                        "Completed - Approved",
                        project_id
                    )

                    break

                if decision == "Rejected":

                    task["status"] = "Rejected"
                    rejected_count += 1

                    update_project_task(task, all_tasks)

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

                    update_project_task(task, all_tasks)

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

                update_project_task(task, all_tasks)

                save_log(
                    employee,
                    "Revising report using auditor feedback",
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

            update_project_task(task, all_tasks)

            save_log(
                employee,
                task["task"],
                f"Failed: {error}",
                project_id
            )

            print(f"FAILED: {employee} - {error}")

    # Step 4: Final Quality Auditor decision
    all_approved = (
        len(specialist_tasks) == 6
        and all(
            task.get("status") == "Completed"
            and task.get("verification_status") == "Approved"
            for task in specialist_tasks
        )
    )

    auditor_task["output"] = {
        "reports_reviewed": review_attempts,
        "approved": approved_count,
        "needs_revision": revision_count,
        "rejected": rejected_count,
        "failed": failed_count
    }

    if all_approved:

        auditor_task["status"] = "Completed"
        auditor_task["verification_status"] = "Approved"

        auditor_task["output"]["final_decision"] = "APPROVED"

        update_project_task(auditor_task, all_tasks)

        save_log(
            "quality-auditor",
            "Final review of all six specialist reports",
            "APPROVED",
            project_id
        )

        # Step 5: Generate consolidated report
        final_report = create_final_report(project_id)

        print("\nFINAL QUALITY DECISION: APPROVED")
        print(f"Final report: {final_report}")

        # Step 6: Email only after final approval
        email_result = send_final_report_email(
            project_id,
            final_report
        )

        print("\nEMAIL DELIVERY RESULT")
        print(f"Status: {email_result['status']}")
        print(f"Message: {email_result['message']}")

        return {
            "project_id": project_id,
            "status": "Quality Approved",
            "final_report": str(final_report),
            "email_status": email_result["status"],
            "email_message": email_result["message"],
            "email_eligible": True
        }

    else:

        auditor_task["status"] = "Needs Revision"
        auditor_task["verification_status"] = "Not Approved"

        auditor_task["output"]["final_decision"] = "NOT APPROVED"

        update_project_task(auditor_task, all_tasks)

        with get_db() as db:

            db.execute("""
                UPDATE projects
                SET status = ?, updated_at = ?
                WHERE project_id = ?
            """, (
                "Quality Review Incomplete",
                current_time(),
                project_id
            ))

        save_log(
            "quality-auditor",
            "Final review of all six specialist reports",
            "NOT APPROVED - Email blocked",
            project_id
        )

        print("\nFINAL QUALITY DECISION: NOT APPROVED")
        print("Final client email is blocked.")

        return {
            "project_id": project_id,
            "status": "Quality Review Incomplete",
            "email_status": "Blocked",
            "email_message": "Final approval was not received.",
            "email_eligible": False
        }


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--project-id",
        required=True
    )

    args = parser.parse_args()

    result = run_project(args.project_id)

    print("\nPROJECT RESULT")
    print(json.dumps(result, indent=4))

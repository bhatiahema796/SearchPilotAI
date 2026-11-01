
import os
import json
import smtplib
from datetime import datetime
from email.message import EmailMessage
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_FILE = os.path.join(BASE_DIR, "logs", "task_logs.json")
TASK_FILE = os.path.join(BASE_DIR, "data", "tasks.json")

EMPLOYEES = [
    "project-manager",
    "keyword-researcher",
    "seo-content-writer",
    "technical-seo-auditor",
    "aeo-specialist",
    "competitor-analyst",
    "performance-analyst",
    "quality-auditor",
]


def read_json(path):
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def parse_timestamp(value):
    try:
        timestamp = datetime.fromisoformat(value)

        if timestamp.tzinfo is None:
            timestamp = timestamp.astimezone()

        return timestamp

    except (ValueError, TypeError):
        return None


def get_qa_result(status):

    if status == "Completed":
        return "Approved"

    if status == "Needs Revision":
        return "Needs Revision"

    if status == "Rejected":
        return "Rejected"

    return status


def generate_daily_report():

    logs = read_json(LOG_FILE)
    tasks = read_json(TASK_FILE)

    if not isinstance(logs, list):
        logs = []

    if not isinstance(tasks, list):
        tasks = []

    today = datetime.now().astimezone().date()

    daily_logs = []
    valid_logs = []

    for entry in logs:

        timestamp = parse_timestamp(
            entry.get("timestamp", "")
        )

        if timestamp is None:
            continue

        valid_logs.append((timestamp, entry))

        if timestamp.date() == today:
            daily_logs.append(entry)

    # ---------------------------------
    # DAILY ACTIVITY COUNTS
    # ---------------------------------

    activity_counts = Counter(
        entry.get("agent_name", "Unknown")
        for entry in daily_logs
    )

    daily_status_counts = Counter(
        entry.get("output_status", "Unknown")
        for entry in daily_logs
    )

    # ---------------------------------
    # QUALITY AUDITOR RESULTS
    # ---------------------------------

    qa_events = []

    for timestamp, entry in valid_logs:

        if entry.get("agent_name") != "quality-auditor":
            continue

        task_description = entry.get(
            "task_performed", ""
        )

        if task_description.startswith("Reviewed report of "):

            employee = task_description.replace(
                "Reviewed report of ", "", 1
            ).strip()

            qa_events.append({
                "timestamp": timestamp,
                "employee": employee,
                "status": entry.get(
                    "output_status", "Unknown"
                ),
            })

    today_qa_events = [
        event for event in qa_events
        if event["timestamp"].date() == today
    ]

    qa_counts = Counter(
        event["status"] for event in today_qa_events
    )

    latest_qa = {}

    for event in qa_events:

        employee = event["employee"]

        if (
            employee not in latest_qa
            or event["timestamp"] > latest_qa[employee]["timestamp"]
        ):
            latest_qa[employee] = event

    # ---------------------------------
    # LATEST EMPLOYEE ACTIVITY
    # ---------------------------------

    latest_employee_activity = {}

    for timestamp, entry in valid_logs:

        employee = entry.get("agent_name", "")

        if employee not in EMPLOYEES:
            continue

        if employee not in latest_employee_activity:

            latest_employee_activity[employee] = {
                "timestamp": timestamp,
                "entry": entry,
            }

        elif timestamp > latest_employee_activity[employee]["timestamp"]:

            latest_employee_activity[employee] = {
                "timestamp": timestamp,
                "entry": entry,
            }

    # ---------------------------------
    # TASK ASSIGNMENTS
    # ---------------------------------

    employee_tasks = {
        task.get("employee"): task
        for task in tasks
        if isinstance(task, dict)
        and task.get("employee")
    }

    employee_status = {}

    for employee in EMPLOYEES:

        # Project Manager is the agency coordinator.
        if employee == "project-manager":

            activity = latest_employee_activity.get(employee)

            employee_status[employee] = {
                "task": "Coordinates all agency employees",
                "status": "Agency Coordinator",
                "last_update": (
                    activity["entry"].get("timestamp", "Unknown")
                    if activity else "No activity recorded"
                ),
            }

            continue

        task = employee_tasks.get(employee, {})

        activity = latest_employee_activity.get(employee)
        qa = latest_qa.get(employee)

        if activity:

            employee_time = activity["timestamp"]
            employee_entry = activity["entry"]

            status = employee_entry.get(
                "output_status", "Unknown"
            )

            last_update = employee_entry.get(
                "timestamp", "Unknown"
            )

        else:

            employee_time = None
            status = "Assigned - No activity logged"
            last_update = "No activity recorded"

        # A later QA decision overrides the employee's
        # earlier submission status.

        if qa and (
            employee_time is None
            or qa["timestamp"] >= employee_time
        ):

            status = get_qa_result(qa["status"])

            last_update = qa["timestamp"].isoformat(
                timespec="seconds"
            )

        employee_status[employee] = {
            "task": task.get(
                "task", "No task assigned"
            ),
            "status": status,
            "last_update": last_update,
        }

    # ---------------------------------
    # AGENCY PERFORMANCE COUNTS
    # ---------------------------------

    specialist_statuses = [
        employee_status[employee]["status"]
        for employee in EMPLOYEES
        if employee not in (
            "project-manager",
            "quality-auditor"
        )
    ]

    completed = sum(
        status in ("Completed", "Approved")
        for status in specialist_statuses
    )

    rejected = specialist_statuses.count("Rejected")

    failed = specialist_statuses.count("Failed")

    pending = (
        len(specialist_statuses)
        - completed
        - rejected
        - failed
    )

    # ---------------------------------
    # QUALITY AUDITOR STATUS
    # ---------------------------------

    auditor_activity = latest_employee_activity.get(
        "quality-auditor"
    )

    auditor_status = (
        auditor_activity["entry"].get(
            "output_status", "Unknown"
        )
        if auditor_activity
        else "No activity logged"
    )

    # ---------------------------------
    # BUILD REPORT
    # ---------------------------------

    report = [

        "SEARCHPILOT AI",

        "DETAILED DAILY AGENCY PERFORMANCE REPORT",

        "=" * 55,

        f"Report Date: {today.strftime('%d %B %Y')}",

        f"Report Generated: {datetime.now().astimezone().strftime('%H:%M:%S')}",

        "",

        "1. AGENCY OVERVIEW",

        "-" * 40,

        "Total Employees: 8",

        "Agency Coordinator: Project Manager",

        f"Specialist Employees: {len(specialist_statuses)}",

        f"Completed / Approved: {completed}",

        f"Pending / In Progress: {pending}",

        f"Rejected: {rejected}",

        f"Failed: {failed}",

        f"Today's Recorded Activities: {len(daily_logs)}",

        "",

        "2. EMPLOYEE-WISE PERFORMANCE",

        "-" * 40,
    ]

    for employee in EMPLOYEES:

        details = employee_status[employee]

        report.extend([

            f"Employee: {employee}",

            f"Assigned Task: {details['task']}",

            f"Latest Status: {details['status']}",

            f"Today's Activities: {activity_counts.get(employee, 0)}",

            f"Last Update: {details['last_update']}",

            "",
        ])

    report.extend([

        "3. QUALITY ASSURANCE SUMMARY",

        "-" * 40,

        f"Quality Auditor Latest Status: {auditor_status}",

        f"Reports Reviewed Today: {len(today_qa_events)}",

        f"Approved Today: {qa_counts.get('Completed', 0)}",

        f"Needs Revision Today: {qa_counts.get('Needs Revision', 0)}",

        f"Rejected Today: {qa_counts.get('Rejected', 0)}",

        "",

        "4. DAILY ACTIVITY SUMMARY",

        "-" * 40,

        f"Completed Activity Entries: {daily_status_counts.get('Completed', 0)}",

        f"Submitted for Review: {daily_status_counts.get('Submitted for Review', 0)}",

        f"Needs Revision Entries: {daily_status_counts.get('Needs Revision', 0)}",

        f"Rejected Entries: {daily_status_counts.get('Rejected', 0)}",

        f"Failed Activity Entries: {daily_status_counts.get('Failed', 0)}",

        "",

        "5. DETAILED DAILY ACTIVITY LOG",

        "-" * 40,
    ])

    if daily_logs:

        for entry in daily_logs:

            report.extend([

                f"Time: {entry.get('timestamp', 'Unknown')}",

                f"Employee: {entry.get('agent_name', 'Unknown')}",

                f"Activity: {entry.get('task_performed', 'Unknown')}",

                f"Status: {entry.get('output_status', 'Unknown')}",

                "-" * 30,
            ])

    else:

        report.append(
            "No activities have been recorded today."
        )

    # ---------------------------------
    # PROJECT MANAGER SUMMARY
    # ---------------------------------

    report.extend([

        "",

        "6. PROJECT MANAGER SUMMARY",

        "-" * 40,

        f"The agency has {len(EMPLOYEES)} registered employees.",

        f"{completed} of {len(specialist_statuses)} specialists are completed or approved.",

        f"{pending} specialists have pending or in-progress work.",

        f"{rejected} specialists have a latest rejected status.",

        f"{failed} specialists have a latest failed status.",

        f"Quality Auditor latest status: {auditor_status}.",

        "",

        "REPORT NOTES",

        "-" * 40,

        "Employee status is based on the latest available activity",

        "and Quality Auditor decision.",

        "Daily activity and QA figures include today's records only.",

        "No unrecorded activity is assumed to have occurred.",

        "",

        "Regards,",

        "SearchPilot AI Project Manager",

        "SEO & AEO Automation Agency",
    ])

    return "\n".join(report)


def send_daily_email():

    sender_email = os.getenv(
        "GMAIL_ADDRESS", ""
    ).strip()

    app_password = os.getenv(
        "GMAIL_APP_PASSWORD", ""
    ).strip().replace(" ", "")

    recipient_email = os.getenv(
        "GMAIL_TO", sender_email
    ).strip()

    if not sender_email or not app_password:

        raise ValueError(
            "Gmail credentials missing in .env"
        )

    body = generate_daily_report()

    message = EmailMessage()

    message["From"] = sender_email

    message["To"] = recipient_email

    message["Subject"] = (
        "SearchPilot AI - Detailed Daily Agency Performance Report"
    )

    message.set_content(body)

    with smtplib.SMTP_SSL(
        "smtp.gmail.com", 465, timeout=30
    ) as server:

        server.login(sender_email, app_password)

        server.send_message(message)

    print("DETAILED DAILY REPORT EMAIL SENT SUCCESSFULLY!")

    print(f"Recipient: {recipient_email}")


if __name__ == "__main__":

    send_daily_email()

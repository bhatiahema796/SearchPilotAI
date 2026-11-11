
import os
import smtplib
from pathlib import Path
from datetime import datetime, timezone
from email.message import EmailMessage
from dotenv import load_dotenv

from shared.project_service import get_project
from database.db import get_db

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

REQUIRED_SPECIALISTS = {
    "keyword-researcher",
    "seo-content-writer",
    "technical-seo-auditor",
    "aeo-specialist",
    "competitor-analyst",
    "performance-analyst",
}


def send_final_report_email(project_id, report_path):
    """Send the final report only after all six specialists are approved."""

    project_data = get_project(project_id)

    if not project_data:
        return {"status": "Blocked", "message": "Project not found."}

    project = project_data["project"]
    tasks = project_data["tasks"]

    specialist_tasks = [
        task for task in tasks
        if task.get("employee") in REQUIRED_SPECIALISTS
    ]

    if len(specialist_tasks) != 6:
        return {
            "status": "Blocked",
            "message": "All six specialist tasks must exist."
        }

    for task in specialist_tasks:
        if task.get("status") != "Completed":
            return {
                "status": "Blocked",
                "message": f"{task.get('employee')} is not completed."
            }

        evidence = task.get("evidence") or {}

        if isinstance(evidence, str):
            import json
            try:
                evidence = json.loads(evidence)
            except (ValueError, TypeError):
                evidence = {}

        if evidence.get("verification_status") != "Approved":
            return {
                "status": "Blocked",
                "message": f"{task.get('employee')} is not approved."
            }

    if project.get("status") != "Quality Approved":
        return {
            "status": "Blocked",
            "message": "Project has not received final Quality Auditor approval."
        }

    report_path = Path(report_path)

    if not report_path.is_absolute():
        report_path = BASE_DIR / report_path

    if not report_path.exists():
        return {
            "status": "Blocked",
            "message": "Final report file does not exist."
        }

    recipient = (
        project.get("email")
        or project.get("client_email")
    )

    if not recipient:
        return {
            "status": "Blocked",
            "message": "Client email address is missing."
        }

    # Gmail settings: use existing .env variable names first.
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    smtp_user = (
        os.getenv("GMAIL_ADDRESS")
        or os.getenv("SMTP_USER")
    )

    smtp_password = (
        os.getenv("GMAIL_APP_PASSWORD")
        or os.getenv("SMTP_PASSWORD")
    )

    email_from = (
        os.getenv("GMAIL_ADDRESS")
        or os.getenv("EMAIL_FROM")
        or smtp_user
    )

    if not all([smtp_user, smtp_password, email_from]):
        return {
            "status": "Not Configured",
            "message": "Gmail settings are missing from .env."
        }

    # Prevent duplicate email delivery.
    with get_db() as db:
        existing = db.execute(
            """
            SELECT id, status FROM email_deliveries
            WHERE project_id = ?
            AND recipient = ?
            AND status = 'Sent'
            LIMIT 1
            """,
            (project_id, recipient)
        ).fetchone()

        if existing:
            return {
                "status": "Already Sent",
                "message": "Final report was already emailed to this client."
            }

        cursor = db.execute(
            """
            INSERT INTO email_deliveries
            (project_id, recipient, subject, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                project_id,
                recipient,
                "SearchPilot AI - Final SEO & AEO Report",
                "Pending",
                datetime.now(timezone.utc).isoformat()
            )
        )
        delivery_id = cursor.lastrowid

    try:
        message = EmailMessage()
        message["Subject"] = "SearchPilot AI - Final SEO & AEO Report"
        message["From"] = email_from
        message["To"] = recipient

        message.set_content(
            "Hello,\n\n"
            "Your SEO and AEO analysis has been completed.\n"
            "All six specialist reports have passed Quality Auditor review.\n\n"
            "Please find the consolidated final report attached.\n\n"
            "Regards,\nSearchPilot AI Team"
        )

        message.add_attachment(
            report_path.read_bytes(),
            maintype="text",
            subtype="markdown",
            filename=report_path.name
        )

        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)

        with get_db() as db:
            db.execute(
                """
                UPDATE email_deliveries
                SET status = 'Sent', sent_at = ?
                WHERE id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), delivery_id)
            )

        return {
            "status": "Sent",
            "message": f"Final report emailed to {recipient}."
        }

    except Exception as error:
        with get_db() as db:
            db.execute(
                """
                UPDATE email_deliveries
                SET status = 'Failed', error = ?
                WHERE id = ?
                """,
                (str(error), delivery_id)
            )

        return {
            "status": "Failed",
            "message": str(error)
        }

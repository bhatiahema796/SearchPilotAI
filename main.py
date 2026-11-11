
import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from shared.task_manager import assign_tasks
from shared.agent_runner import execute_pending_tasks
from integrations.google_sheets import log_activity

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config" / "agency.json"
LOG_FILE = BASE_DIR / "logs" / "task_logs.json"


def save_log(agent_name, task, status):
    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    log_entry = {
        "timestamp": timestamp,
        "agent_name": agent_name,
        "task_performed": task,
        "output_status": status
    }

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logs = []

    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as file:
                logs = json.load(file)
            if not isinstance(logs, list):
                logs = []
        except (json.JSONDecodeError, OSError):
            logs = []

    logs.append(log_entry)

    with open(LOG_FILE, "w", encoding="utf-8") as file:
        json.dump(logs, file, indent=4, ensure_ascii=False)

    print(f"LOCAL LOG SAVED: {agent_name} - {status}")

    try:
        log_activity(
            timestamp,
            agent_name,
            task,
            status
        )
    except Exception as error:
        print(f"Google Sheets logging warning: {error}")
        print("Local log is safe.")


def load_agency():
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def show_employees(agency):
    print("\nSEARCHPILOT AI")
    print("=" * 45)
    print("Agency:", agency["agency_name"])
    print("Total Employees:", agency["total_employees"])

    print("\nRegistered AI Employees:")

    for number, employee in enumerate(
        agency["employees"], start=1
    ):
        print(f"{number}. {employee}")


def validate_website(website):
    parsed = urlparse(website.strip())

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            "Website must begin with https:// or http://"
        )

    if not parsed.hostname:
        raise ValueError("Please enter a valid website URL.")

    return website.strip()


def get_client_details(args):
    print("\nNEW CLIENT PROJECT")
    print("=" * 45)

    business_name = args.business_name

    if not business_name:
        business_name = input("Enter business name: ").strip()

    website = args.website

    if not website:
        website = input("Enter website URL: ").strip()

    if not business_name:
        raise ValueError("Business name cannot be empty.")

    website = validate_website(website)

    return business_name, website


def main():
    parser = argparse.ArgumentParser(
        description="SearchPilot AI SEO and AEO Agency"
    )

    parser.add_argument("--business-name")
    parser.add_argument("--website")
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="Create tasks without executing employees."
    )

    args = parser.parse_args()

    agency = load_agency()
    show_employees(agency)

    business_name, website = get_client_details(args)

    print("\nPROJECT MANAGER: Creating client project")
    print("Business:", business_name)
    print("Website:", website)

    tasks = assign_tasks(
        business_name=business_name,
        website=website
    )

    save_log(
        "project-manager",
        f"Created project and assigned {len(tasks)} tasks for {business_name}",
        "Completed"
    )

    if args.no_run:
        print("\nTasks created. Execution skipped.")
        return

    print("\nPROJECT MANAGER: Starting employee execution")

    execute_pending_tasks()

    print("\nPROJECT MANAGER: Execution process finished.")
    print("Check data/tasks.json and reports/ for results.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(f"\nPROJECT ERROR: {error}")


import json
from pathlib import Path
from datetime import datetime

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
        with open(LOG_FILE, "r", encoding="utf-8") as file:
            logs = json.load(file)

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
    print("=" * 40)
    print("Agency:", agency["agency_name"])
    print("Total Employees:", agency["total_employees"])

    print("\nRegistered AI Employees:")

    for number, employee in enumerate(
        agency["employees"], start=1
    ):
        print(f"{number}. {employee}")


def main():
    agency = load_agency()

    show_employees(agency)

    print("\nPROJECT MANAGER: Initializing")

    save_log(
        "project-manager",
        "Initialized SearchPilot AI execution system",
        "Completed"
    )

    print("\nPROJECT MANAGER: Assigning Tasks")

    tasks = assign_tasks(
        business_name="Glow Nest Candle Studio",
        website="https://example.com"
    )

    save_log(
        "project-manager",
        f"Assigned {len(tasks)} specialist tasks",
        "Completed"
    )

    print("\nPROJECT MANAGER: Starting employee execution")

    execute_pending_tasks()

    print("\nPROJECT MANAGER: All tasks processed.")
    print("Check data/tasks.json and reports/ for results.")


if __name__ == "__main__":
    main()

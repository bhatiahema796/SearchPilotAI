
import json
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent.parent

CREDENTIALS_FILE = (
    BASE_DIR / "integrations" / "google_service_account.json"
)

# Your Google Spreadsheet ID
SPREADSHEET_ID = "1VewDGhMGjMOybY_MlR9aWM5l9OfUN43Qip1d3NHrjxk"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]


def get_sheets_service():
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            "Google Service Account JSON file not found."
        )

    credentials = Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES
    )

    return build("sheets", "v4", credentials=credentials)


def setup_headers():
    service = get_sheets_service()

    values = [[
        "Timestamp",
        "Agent Name",
        "Task Performed",
        "Output Status"
    ]]

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A1:D1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

    print("Google Sheets headers verified successfully.")


def log_activity(timestamp, agent_name, task_performed, output_status):
    service = get_sheets_service()

    values = [[
        timestamp,
        agent_name,
        task_performed,
        output_status
    ]]

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A:D",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values}
    ).execute()

    print(f"Google Sheets log saved: {agent_name}")

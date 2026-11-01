
@echo off

cd /d "C:\Users\simran\Downloads\SearchPilotAI"

".venv\Scripts\python.exe" "integrations\email_report.py" >> "logs\daily_email.log" 2>&1

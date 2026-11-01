import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="SearchPilot AI Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"

TASKS_FILE = DATA_DIR / "tasks.json"
LOGS_FILE = LOGS_DIR / "task_logs.json"


# =====================================================
# LOAD DATA
# =====================================================

def load_json(file_path):
    """Load JSON data safely."""
    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
    except Exception as error:
        st.warning(f"Could not read {file_path.name}: {error}")

    return []


def to_records(data):
    """Convert common JSON structures into a list of records."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    if isinstance(data, dict):
        for key in ("tasks", "logs", "records", "data", "results"):
            if isinstance(data.get(key), list):
                return [
                    item for item in data[key]
                    if isinstance(item, dict)
                ]

        if any(
            key in data
            for key in ("task", "employee", "agent_name", "timestamp")
        ):
            return [data]

    return []


task_data = to_records(load_json(TASKS_FILE))
log_data = to_records(load_json(LOGS_FILE))


# =====================================================
# EMPLOYEE INFORMATION
# =====================================================

employees = [
    {
        "name": "Project Manager",
        "id": "project-manager",
        "role": "Task coordination and management",
        "icon": "👩‍💼"
    },
    {
        "name": "Keyword Researcher",
        "id": "keyword-researcher",
        "role": "SEO keyword research",
        "icon": "🔎"
    },
    {
        "name": "SEO Content Writer",
        "id": "seo-content-writer",
        "role": "SEO content creation",
        "icon": "✍️"
    },
    {
        "name": "Technical SEO Auditor",
        "id": "technical-seo-auditor",
        "role": "Technical SEO analysis",
        "icon": "🛠️"
    },
    {
        "name": "AEO Specialist",
        "id": "aeo-specialist",
        "role": "Answer Engine Optimization",
        "icon": "🤖"
    },
    {
        "name": "Competitor Analyst",
        "id": "competitor-analyst",
        "role": "Competitor research",
        "icon": "📊"
    },
    {
        "name": "Performance Analyst",
        "id": "performance-analyst",
        "role": "Performance analysis",
        "icon": "📈"
    },
    {
        "name": "Quality Auditor",
        "id": "quality-auditor",
        "role": "Quality review and approval",
        "icon": "✅"
    }
]


# =====================================================
# NORMALIZE DATA
# =====================================================

def get_value(record, possible_keys, default="Not available"):
    for key in possible_keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return default


def normalize_tasks(records):
    normalized = []

    for record in records:
        normalized.append({
            "Employee": get_value(
                record, ["employee", "agent_name", "agent", "assigned_to"]
            ),
            "Task": get_value(
                record, ["task", "task_performed", "description", "title"]
            ),
            "Status": get_value(
                record, ["status", "output_status", "output"]
            ),
            "Created At": get_value(
                record, ["created_at", "timestamp", "date"]
            )
        })

    return normalized


def normalize_logs(records):
    normalized = []

    for record in records:
        normalized.append({
            "Timestamp": get_value(
                record, ["timestamp", "created_at", "date"]
            ),
            "Agent Name": get_value(
                record, ["agent_name", "employee", "agent"]
            ),
            "Task Performed": get_value(
                record, ["task_performed", "task", "description"]
            ),
            "Output Status": get_value(
                record, ["output_status", "status"]
            )
        })

    return normalized


tasks = normalize_tasks(task_data)
logs = normalize_logs(log_data)

tasks_df = pd.DataFrame(tasks)
logs_df = pd.DataFrame(logs)


# =====================================================
# CUSTOM DESIGN
# =====================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #f5f7ff 0%, #eef2ff 100%);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #171936 0%, #29265c 100%);
    }

    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        padding: 8px 10px;
        border-radius: 9px;
    }

    .main-title {
        font-family: 'Outfit', sans-serif;
        font-size: 37px;
        font-weight: 800;
        color: #ffffff;
        margin-top: 5px;
    }

    .main-subtitle {
        color: #e0e7ff;
        font-size: 15px;
        margin-top: 5px;
    }

    .top-label {
        color: #c7d2fe;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 3px;
    }

    .hero {
        background: linear-gradient(115deg, #191c43, #4140a4 58%, #348bc4);
        padding: 30px 34px;
        border-radius: 20px;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px rgba(49, 47, 125, 0.17);
    }

    .hero-footer {
        color: #c7d5ff;
        font-size: 11px;
        margin-top: 19px;
        letter-spacing: 1px;
    }

    .section-title {
        font-family: 'Outfit', sans-serif;
        color: #20234b;
        font-size: 23px;
        font-weight: 700;
        margin: 15px 0 12px 0;
    }

    .employee-card {
        background: #ffffff;
        border: 1px solid #e5e9f8;
        border-radius: 15px;
        padding: 17px;
        min-height: 125px;
        box-shadow: 0 5px 16px rgba(30, 41, 90, 0.05);
        margin-bottom: 12px;
    }

    .employee-name {
        color: #22264f;
        font-weight: 700;
        font-size: 15px;
        margin-top: 8px;
    }

    .employee-role {
        color: #777f9c;
        font-size: 12px;
        margin-top: 5px;
    }

    .small-note {
        color: #777f9c;
        font-size: 12px;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e4e8f5;
        border-radius: 15px;
        padding: 16px 18px;
        box-shadow: 0 5px 16px rgba(30, 41, 90, 0.05);
    }

    div[data-testid="stMetricLabel"] {
        color: #69718d;
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        color: #282b61;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
    }

    div[data-testid="stDataFrame"] {
        background: #ffffff;
        border-radius: 12px;
    }

    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 12px 5px 24px 5px;">
            <div style="font-size:30px;">🚀</div>
            <div style="
                font-family:Outfit;
                font-size:23px;
                font-weight:800;
                color:white;
            ">
                SearchPilot AI
            </div>
            <div style="font-size:11px;color:#c7c9ee;">
                SEO & AEO AUTOMATION AGENCY
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    page = st.radio(
        "WORKSPACE",
        [
            "Overview",
            "Employees",
            "Tasks",
            "Quality Assurance",
            "Activity Logs",
            "Reports"
        ],
        label_visibility="visible"
    )

    st.markdown("---")

    st.caption("SYSTEM INFORMATION")
    st.write("👥 8 Registered Employees")
    st.write("📋 Local Task Records")
    st.write("🔗 Google Sheets Logging")

    st.markdown("---")
    st.caption("SearchPilot AI | 2026")


# =====================================================
# HEADER
# =====================================================

st.markdown(
    """
    <div class="hero">
        <div class="top-label">BUSINESS WORKSPACE</div>
        <div class="main-title">SearchPilot AI</div>
        <div class="main-subtitle">
            SEO &amp; AEO Automation Agency
        </div>
        <div class="hero-footer">
            EMPLOYEE MANAGEMENT &bull;
            TASK AUTOMATION &bull;
            QUALITY CONTROL
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def show_section(title, description=None):
    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True
    )

    if description:
        st.caption(description)


def status_count(dataframe, status):
    if dataframe.empty or "Status" not in dataframe.columns:
        return 0

    return int(
        dataframe["Status"]
        .astype(str)
        .str.lower()
        .str.contains(status.lower(), na=False)
        .sum()
    )


def show_empty_message(message):
    st.info(message)


# =====================================================
# OVERVIEW PAGE
# =====================================================

if page == "Overview":

    show_section(
        "Agency Overview",
        "A central workspace for monitoring your AI employees and their activities."
    )

    total_employees = len(employees)
    total_tasks = len(tasks_df)

    completed_tasks = status_count(tasks_df, "completed")
    pending_tasks = status_count(tasks_df, "pending")
    failed_tasks = status_count(tasks_df, "failed")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("AI Employees", total_employees)
    col2.metric("Total Tasks", total_tasks)
    col3.metric("Completed Tasks", completed_tasks)
    col4.metric("Failed Tasks", failed_tasks)

    st.markdown("---")

    left, right = st.columns([1.2, 1])

    with left:
        show_section("Employee Directory")

        for employee in employees:
            st.markdown(
                f"""
                <div class="employee-card">
                    <div style="font-size:23px;">
                        {employee["icon"]}
                    </div>
                    <div class="employee-name">
                        {employee["name"]}
                    </div>
                    <div class="employee-role">
                        {employee["role"]}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with right:
        show_section("Task Status")

        if not tasks_df.empty:
            status_data = (
                tasks_df["Status"]
                .astype(str)
                .value_counts()
                .reset_index()
            )

            status_data.columns = ["Status", "Count"]

            st.bar_chart(
                status_data.set_index("Status"),
                use_container_width=True
            )

            st.dataframe(
                status_data,
                use_container_width=True,
                hide_index=True
            )
        else:
            show_empty_message(
                "No task records found yet. Run your agency to generate task data."
            )

        show_section("Recent Activity")

        if not logs_df.empty:
            st.dataframe(
                logs_df.tail(5).iloc[::-1],
                use_container_width=True,
                hide_index=True
            )
        else:
            show_empty_message("No activity logs found yet.")


# =====================================================
# EMPLOYEES PAGE
# =====================================================

elif page == "Employees":

    show_section(
        "AI Employee Directory",
        "The eight registered employees of SearchPilot AI."
    )

    columns = st.columns(2)

    for index, employee in enumerate(employees):
        with columns[index % 2]:
            st.markdown(
                f"""
                <div class="employee-card">
                    <div style="font-size:27px;">
                        {employee["icon"]}
                    </div>
                    <div class="employee-name">
                        {employee["name"]}
                    </div>
                    <div class="employee-role">
                        {employee["role"]}
                    </div>
                    <div style="
                        color:#25865c;
                        font-size:11px;
                        font-weight:700;
                        margin-top:12px;
                    ">
                        REGISTERED
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.caption(
        "Employee registration is displayed here. "
        "This does not independently confirm that an employee is currently running."
    )


# =====================================================
# TASKS PAGE
# =====================================================

elif page == "Tasks":

    show_section(
        "Task Management",
        "View tasks recorded by the agency."
    )

    if not tasks_df.empty:

        search_text = st.text_input(
            "Search tasks or employees",
            placeholder="Enter employee name or task..."
        )

        filtered_tasks = tasks_df.copy()

        if search_text:
            mask = (
                filtered_tasks.astype(str)
                .apply(
                    lambda column: column.str.contains(
                        search_text,
                        case=False,
                        na=False
                    )
                )
                .any(axis=1)
            )
            filtered_tasks = filtered_tasks[mask]

        st.dataframe(
            filtered_tasks,
            use_container_width=True,
            hide_index=True
        )

        csv_data = filtered_tasks.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Task Records",
            data=csv_data,
            file_name="searchpilot_tasks.csv",
            mime="text/csv"
        )

    else:
        show_empty_message(
            "No task records are available. Run the Project Manager workflow first."
        )


# =====================================================
# QUALITY ASSURANCE PAGE
# =====================================================

elif page == "Quality Assurance":

    show_section(
        "Quality Assurance",
        "Review the recorded quality-audit activity."
    )

    qa_logs = []

    for record in log_data:
        agent = str(
            get_value(
                record,
                ["agent_name", "employee", "agent"],
                ""
            )
        ).lower()

        if "quality-auditor" in agent or "quality auditor" in agent:
            qa_logs.append(record)

    if qa_logs:
        qa_df = pd.DataFrame(normalize_logs(qa_logs))

        st.metric("Recorded QA Activities", len(qa_df))

        st.dataframe(
            qa_df.iloc[::-1],
            use_container_width=True,
            hide_index=True
        )
    else:
        show_empty_message(
            "No Quality Auditor activity has been recorded in the local log yet."
        )

    st.markdown("---")
    st.caption(
        "The dashboard displays recorded QA results. "
        "It does not independently verify the factual accuracy of reports."
    )


# =====================================================
# ACTIVITY LOGS PAGE
# =====================================================

elif page == "Activity Logs":

    show_section(
        "Employee Activity Logs",
        "Activity records saved by the agency."
    )

    if not logs_df.empty:

        st.metric("Total Recorded Activities", len(logs_df))

        employee_options = sorted(
            logs_df["Agent Name"].astype(str).unique().tolist()
        )

        selected_employee = st.selectbox(
            "Filter by employee",
            ["All Employees"] + employee_options
        )

        filtered_logs = logs_df.copy()

        if selected_employee != "All Employees":
            filtered_logs = filtered_logs[
                filtered_logs["Agent Name"] == selected_employee
            ]

        st.dataframe(
            filtered_logs.iloc[::-1],
            use_container_width=True,
            hide_index=True
        )

        csv_data = filtered_logs.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Activity Logs",
            data=csv_data,
            file_name="searchpilot_activity_logs.csv",
            mime="text/csv"
        )

    else:
        show_empty_message(
            "No local activity logs found. "
            "Employee activity will appear here after execution."
        )


# =====================================================
# REPORTS PAGE
# =====================================================

elif page == "Reports":

    show_section(
        "Agency Reports",
        "Reports saved in the project's reports folder."
    )

    if REPORTS_DIR.exists():

        report_files = sorted(
            [
                file for file in REPORTS_DIR.iterdir()
                if file.is_file()
            ],
            key=lambda file: file.stat().st_mtime,
            reverse=True
        )

        st.metric("Available Report Files", len(report_files))

        if report_files:

            for report in report_files:

                with st.expander(f"📄 {report.name}"):

                    if report.suffix.lower() in [".txt", ".md"]:
                        try:
                            content = report.read_text(
                                encoding="utf-8",
                                errors="replace"
                            )
                            st.text(content[:12000])
                        except Exception:
                            st.warning("Could not preview this report.")

                    elif report.suffix.lower() == ".json":
                        try:
                            content = json.loads(
                                report.read_text(encoding="utf-8")
                            )
                            st.json(content)
                        except Exception:
                            st.warning("Could not preview this JSON report.")

                    else:
                        st.caption(
                            "Preview is not available for this file type."
                        )

                    try:
                        file_bytes = report.read_bytes()

                        st.download_button(
                            "Download Report",
                            data=file_bytes,
                            file_name=report.name,
                            key=f"download_{report.name}"
                        )
                    except Exception:
                        st.warning("Could not prepare this report for download.")

        else:
            show_empty_message("No report files are available yet.")

    else:
        show_empty_message("The reports folder has not been created yet.")


# =====================================================
# FOOTER
# =====================================================

st.markdown("---")

st.markdown(
    """
    <div style="
        text-align:center;
        color:#858ba8;
        font-size:12px;
        padding:10px;
    ">
        SearchPilot AI &nbsp; | &nbsp;
        SEO & AEO Automation Agency &nbsp; | &nbsp;
        2026
    </div>
    """,
    unsafe_allow_html=True
)
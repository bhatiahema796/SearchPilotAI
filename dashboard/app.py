
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="SearchPilot AI Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
TASKS_FILE = DATA_DIR / "tasks.json"
DB_FILE = DATA_DIR / "searchpilot.db"

sys.path.insert(0, str(BASE_DIR))

from shared.project_service import create_project
from shared.project_runner import run_project


# =====================================================
# EMPLOYEES
# =====================================================

EMPLOYEES = [
    ("Project Manager", "project-manager", "👩‍💼", "Task coordination"),
    ("Keyword Researcher", "keyword-researcher", "🔎", "SEO keyword research"),
    ("SEO Content Writer", "seo-content-writer", "✍️", "SEO content creation"),
    ("Technical SEO Auditor", "technical-seo-auditor", "🛠️", "Technical SEO"),
    ("AEO Specialist", "aeo-specialist", "🤖", "Answer Engine Optimization"),
    ("Competitor Analyst", "competitor-analyst", "📊", "Competitor research"),
    ("Performance Analyst", "performance-analyst", "📈", "Performance analysis"),
    ("Quality Auditor", "quality-auditor", "✅", "Quality verification")
]


# =====================================================
# DATABASE
# =====================================================

def get_connection():
    connection = sqlite3.connect(DB_FILE, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_all(query, params=()):
    with get_connection() as connection:
        return [
            dict(row)
            for row in connection.execute(query, params).fetchall()
        ]


def fetch_one(query, params=()):
    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()
        return dict(row) if row else None


def load_json_file(path, default=None):
    if default is None:
        default = []

    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass

    return default


def parse_json(value):
    if isinstance(value, (dict, list)):
        return value

    if not value:
        return {}

    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return {}


def load_dashboard_data():
    projects = fetch_all("""
        SELECT
            p.project_id,
            p.client_id,
            c.company_name,
            c.email,
            p.website_url,
            p.category,
            p.country,
            p.audience,
            p.services,
            p.seo_goals,
            p.competitors,
            p.status,
            p.created_at,
            p.updated_at
        FROM projects p
        LEFT JOIN clients c ON p.client_id = c.id
        ORDER BY p.created_at DESC
    """)

    tasks = fetch_all("""
        SELECT *
        FROM tasks
        ORDER BY created_at DESC
    """)

    logs = fetch_all("""
        SELECT *
        FROM activity_logs
        ORDER BY timestamp DESC
    """)

    evidence = fetch_all("""
        SELECT *
        FROM website_evidence
        ORDER BY collected_at DESC
    """)

    reports = fetch_all("""
        SELECT *
        FROM reports
        ORDER BY created_at DESC
    """)

    try:
        emails = fetch_all("""
            SELECT *
            FROM email_deliveries
            ORDER BY created_at DESC
        """)
    except sqlite3.Error:
        emails = []

    return projects, tasks, logs, evidence, reports, emails


# =====================================================
# DESIGN
# =====================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: linear-gradient(135deg,#f5f7ff,#eef2ff);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#171936,#29265c);
}

[data-testid="stSidebar"] * {
    color: white;
}

.hero {
    background: linear-gradient(115deg,#191c43,#4140a4 58%,#348bc4);
    padding: 30px 34px;
    border-radius: 20px;
    margin-bottom: 24px;
    box-shadow: 0 10px 25px rgba(49,47,125,.17);
}

.hero-label {
    color: #c7d2fe;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
}

.hero-title {
    font-family: Outfit;
    font-size: 36px;
    font-weight: 800;
    color: white;
}

.hero-subtitle {
    color: #e0e7ff;
    font-size: 15px;
}

.section-title {
    font-family: Outfit;
    color: #20234b;
    font-size: 23px;
    font-weight: 700;
    margin: 15px 0;
}

.employee-card {
    background: white;
    border: 1px solid #e5e9f8;
    border-radius: 15px;
    padding: 17px;
    min-height: 115px;
    margin-bottom: 12px;
    box-shadow: 0 5px 16px rgba(30,41,90,.05);
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

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e4e8f5;
    border-radius: 15px;
    padding: 16px;
    box-shadow: 0 5px 16px rgba(30,41,90,.05);
}

h1, h2, h3 {
    font-family: Outfit;
}
</style>
""", unsafe_allow_html=True)


def section(title, description=None):
    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True
    )
    if description:
        st.caption(description)


def show_table(data, message="No records available."):
    if data:
        st.dataframe(
            pd.DataFrame(data),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(message)


# =====================================================
# LOAD DATA
# =====================================================

try:
    (
        projects,
        all_tasks,
        all_logs,
        all_evidence,
        all_reports,
        all_emails
    ) = load_dashboard_data()

    db_error = None

except Exception as error:
    projects = []
    all_tasks = []
    all_logs = []
    all_evidence = []
    all_reports = []
    all_emails = []
    db_error = str(error)


local_tasks = load_json_file(TASKS_FILE, [])

local_task_lookup = {
    task.get("task_id"): task
    for task in local_tasks
    if task.get("task_id")
}


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.markdown("""
    <div style="padding:12px 5px 24px 5px;">
        <div style="font-size:30px;">🚀</div>
        <div style="font-family:Outfit;font-size:23px;font-weight:800;">
            SearchPilot AI
        </div>
        <div style="font-size:11px;color:#c7c9ee;">
            SEO & AEO AUTOMATION AGENCY
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "WORKSPACE",
        [
            "Overview",
            "New Client Registration",
            "Projects",
            "Employees",
            "Tasks",
            "Quality Assurance",
            "Activity Logs",
            "Reports",
            "Email Deliveries",
            "Website Evidence"
        ]
    )

    st.markdown("---")
    st.write("👥 8 AI Employees")
    st.write("🗄️ SQLite Database")
    st.write("🔗 Google Sheets Logging")

    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        st.rerun()


if db_error:
    st.error(f"Database connection error: {db_error}")
    st.stop()


# =====================================================
# CLIENT REGISTRATION
# =====================================================

if page == "New Client Registration":

    st.markdown("""
    <div class="hero">
        <div class="hero-label">CLIENT ONBOARDING</div>
        <div class="hero-title">Register New Client</div>
        <div class="hero-subtitle">
            Create a separate SEO and AEO automation project.
        </div>
    </div>
    """, unsafe_allow_html=True)

    section(
        "Client Information",
        "Enter the business details to create a new project."
    )

    with st.form("new_client_form"):

        col1, col2 = st.columns(2)

        with col1:
            company_name = st.text_input(
                "Company / Business Name *"
            )

            client_email = st.text_input(
                "Client Email Address *"
            )

            website_url = st.text_input(
                "Website URL *",
                placeholder="https://example.com"
            )

            category = st.text_input(
                "Business Category"
            )

        with col2:
            country = st.text_input("Country")
            audience = st.text_area("Target Audience")
            services = st.text_area("Products / Services")

        seo_goals = st.text_area(
            "SEO and AEO Goals",
            placeholder="Describe what the client wants to achieve..."
        )

        competitors = st.text_area(
            "Competitor Websites",
            placeholder="Enter competitor websites separated by commas."
        )

        submitted = st.form_submit_button(
            "🚀 Register Client & Create Project",
            use_container_width=True
        )

        if submitted:

            if not company_name.strip():
                st.error("Company name is required.")

            elif not client_email.strip() or "@" not in client_email:
                st.error("Enter a valid client email address.")

            elif not website_url.strip().startswith(("http://", "https://")):
                st.error("Website URL must start with http:// or https://.")

            else:

                try:
                    result = create_project(
                        company_name=company_name.strip(),
                        website_url=website_url.strip(),
                        email=client_email.strip(),
                        category=category.strip(),
                        country=country.strip(),
                        audience=audience.strip(),
                        services=services.strip(),
                        seo_goals=seo_goals.strip(),
                        competitors=competitors.strip()
                    )

                    st.session_state["new_project_id"] = result["project_id"]

                    st.success(
                        f"Client registered successfully! "
                        f"Project ID: {result['project_id']}"
                    )

                    st.write("**Company:**", result["company_name"])
                    st.write("**Website:**", result["website_url"])
                    st.write("**Initial Status:**", result["status"])

                    st.info(
                        "Seven project tasks have been created. "
                        "Refresh the dashboard to see the new project."
                    )

                except Exception as error:
                    st.error(f"Client registration failed: {error}")

    if st.session_state.get("new_project_id"):
        st.write(
            "Latest Project ID:",
            st.session_state["new_project_id"]
        )


# =====================================================
# PROJECT SELECTOR FOR OTHER PAGES
# =====================================================

else:

    st.markdown("""
    <div class="hero">
        <div class="hero-label">BUSINESS WORKSPACE</div>
        <div class="hero-title">SearchPilot AI</div>
        <div class="hero-subtitle">
            SEO & AEO Automation Agency
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not projects:
        st.warning("No client projects found. Register your first client.")
        st.stop()

    project_options = {
        f'{p["company_name"] or "Unknown Client"} | {p["project_id"]}': p
        for p in projects
    }

    selected_label = st.sidebar.selectbox(
        "SELECT CLIENT PROJECT",
        list(project_options.keys())
    )

    selected_project = project_options[selected_label]
    project_id = selected_project["project_id"]

    project_tasks = [
        task for task in all_tasks
        if task["project_id"] == project_id
    ]

    project_logs = [
        log for log in all_logs
        if log["project_id"] == project_id
    ]

    project_evidence = [
        item for item in all_evidence
        if item["project_id"] == project_id
    ]

    project_reports = [
        report for report in all_reports
        if report["project_id"] == project_id
    ]

    project_emails = [
        email for email in all_emails
        if email["project_id"] == project_id
    ]

    st.caption(
        f'Client: {selected_project["company_name"]} | '
        f'Project ID: {project_id}'
    )


    # =================================================
    # OVERVIEW
    # =================================================

    if page == "Overview":

        section("Agency Overview")

        completed = sum(
            1 for task in project_tasks
            if task["status"] == "Completed"
        )

        failed = sum(
            1 for task in project_tasks
            if task["status"] == "Failed"
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("AI Employees", 8)
        col2.metric("Project Tasks", len(project_tasks))
        col3.metric("Completed Tasks", completed)
        col4.metric("Failed Tasks", failed)

        st.markdown("---")

        left, right = st.columns(2)

        with left:
            section("Client Information")

            st.write("**Company:**", selected_project["company_name"])
            st.write("**Email:**", selected_project["email"])
            st.write("**Website:**", selected_project["website_url"])
            st.write("**Project ID:**", project_id)
            st.write("**Status:**", selected_project["status"])
            st.write("**Country:**", selected_project["country"])

        with right:
            section("Task Status")

            if project_tasks:
                counts = (
                    pd.DataFrame(project_tasks)["status"]
                    .value_counts()
                )
                st.bar_chart(counts)

        st.markdown("---")
        section("AI Employee Directory")

        columns = st.columns(4)

        for index, employee in enumerate(EMPLOYEES):
            with columns[index % 4]:
                st.markdown(
                    f"""
                    <div class="employee-card">
                        <div style="font-size:25px;">{employee[2]}</div>
                        <div class="employee-name">{employee[0]}</div>
                        <div class="employee-role">{employee[3]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        section("Recent Activity")

        show_table([
            {
                "Timestamp": log["timestamp"],
                "Agent": log["agent_name"],
                "Task": log["task_performed"],
                "Status": log["output_status"]
            }
            for log in project_logs[:10]
        ])


    # =================================================
    # PROJECTS
    # =================================================

    elif page == "Projects":

        section("All Client Projects")

        project_rows = []

        for project in projects:

            tasks = [
                task for task in all_tasks
                if task["project_id"] == project["project_id"]
            ]

            project_rows.append({
                "Project ID": project["project_id"],
                "Client": project["company_name"],
                "Email": project["email"],
                "Website": project["website_url"],
                "Status": project["status"],
                "Total Tasks": len(tasks),
                "Completed": sum(
                    1 for task in tasks
                    if task["status"] == "Completed"
                ),
                "Created": project["created_at"]
            })

        show_table(project_rows)

        section("Selected Project Details")

        st.json({
            "company": selected_project["company_name"],
            "email": selected_project["email"],
            "website": selected_project["website_url"],
            "category": selected_project["category"],
            "country": selected_project["country"],
            "audience": selected_project["audience"],
            "services": selected_project["services"],
            "seo_goals": selected_project["seo_goals"],
            "competitors": selected_project["competitors"]
        })

        st.markdown("---")
        section("Project Execution")

        st.warning(
            "Running a project starts website crawling, AI specialist execution "
            "and Quality Auditor verification. It may take some time."
        )

        if st.button(
            "▶ Run Project Manager Workflow",
            type="primary",
            use_container_width=True
        ):

            try:
                with st.spinner(
                    "Project Manager is coordinating the AI employees..."
                ):
                    result = run_project(project_id)

                st.success("Project workflow finished.")
                st.json(result)

                st.info(
                    "Refresh the dashboard to load updated task, QA and email records."
                )

            except Exception as error:
                st.error(f"Project execution error: {error}")


    # =================================================
    # EMPLOYEES
    # =================================================

    elif page == "Employees":

        section("AI Employee Directory")

        columns = st.columns(2)

        for index, employee in enumerate(EMPLOYEES):

            employee_tasks = [
                task for task in project_tasks
                if task["employee"] == employee[1]
            ]

            status = (
                employee_tasks[0]["status"]
                if employee_tasks
                else "No task assigned"
            )

            with columns[index % 2]:

                st.markdown(
                    f"""
                    <div class="employee-card">
                        <div style="font-size:27px;">{employee[2]}</div>
                        <div class="employee-name">{employee[0]}</div>
                        <div class="employee-role">{employee[3]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.write("**Task Status:**", status)


    # =================================================
    # TASKS
    # =================================================

    elif page == "Tasks":

        section("Project Task Management")

        if project_tasks:

            search = st.text_input("Search employee or task")

            statuses = sorted({
                str(task["status"])
                for task in project_tasks
            })

            status_filter = st.selectbox(
                "Filter by status",
                ["All"] + statuses
            )

            filtered = []

            for task in project_tasks:

                if status_filter != "All" and task["status"] != status_filter:
                    continue

                if search:
                    content = (
                        str(task["employee"]) + " " +
                        str(task["description"])
                    ).lower()

                    if search.lower() not in content:
                        continue

                filtered.append(task)

            show_table([
                {
                    "Task ID": task["task_id"],
                    "Employee": task["employee"],
                    "Description": task["description"],
                    "Status": task["status"],
                    "Created": task["created_at"],
                    "Completed": task["completed_at"]
                }
                for task in filtered
            ])

            for task in filtered:

                with st.expander(
                    f'{task["employee"]} | {task["status"]}'
                ):

                    st.write("**Description:**", task["description"])

                    if task["output"]:
                        st.text(str(task["output"])[:5000])

                    if task["error"]:
                        st.error(task["error"])

        else:
            st.info("No tasks found.")


    # =================================================
    # QUALITY ASSURANCE
    # =================================================

    elif page == "Quality Assurance":

        section("Quality Auditor Verification")

        specialist_rows = []

        for task in project_tasks:

            local = local_task_lookup.get(
                task["task_id"], {}
            )

            if task["employee"] == "quality-auditor":
                qa_task = task
            else:
                qa_task = None

            if task["employee"] != "quality-auditor":

                specialist_rows.append({
                    "Employee": task["employee"],
                    "Task Status": task["status"],
                    "Verification": local.get(
                        "verification_status",
                        "Not recorded"
                    ),
                    "Revision Attempts": local.get(
                        "revision_attempts",
                        0
                    ),
                    "Error": task["error"] or "None"
                })

        qa_task = next(
            (
                task for task in project_tasks
                if task["employee"] == "quality-auditor"
            ),
            None
        )

        if qa_task:

            st.metric(
                "Quality Auditor Status",
                qa_task["status"]
            )

            qa_output = parse_json(qa_task["output"])

            if qa_output:
                st.json(qa_output)

        show_table(specialist_rows)

        approved = sum(
            1 for row in specialist_rows
            if row["Task Status"] == "Completed"
            and row["Verification"] == "Approved"
        )

        st.metric("Approved Specialist Reports", f"{approved}/6")


    # =================================================
    # ACTIVITY LOGS
    # =================================================

    elif page == "Activity Logs":

        section("Employee Activity Logs")

        show_table([
            {
                "Timestamp": log["timestamp"],
                "Agent": log["agent_name"],
                "Task": log["task_performed"],
                "Status": log["output_status"]
            }
            for log in project_logs
        ])


    # =================================================
    # REPORTS
    # =================================================

    elif page == "Reports":

        section("Generated Reports")

        show_table(project_reports)

        report_folder = REPORTS_DIR / project_id

        if report_folder.exists():

            for report_file in sorted(report_folder.glob("*.md")):

                with st.expander(f"📄 {report_file.name}"):

                    content = report_file.read_text(
                        encoding="utf-8",
                        errors="replace"
                    )

                    st.markdown(content[:12000])

                    st.download_button(
                        "Download Report",
                        data=content.encode("utf-8"),
                        file_name=report_file.name,
                        mime="text/markdown",
                        key=f"download_{project_id}_{report_file.name}"
                    )

        else:
            st.info("No report files found for this project.")


    # =================================================
    # EMAIL DELIVERIES
    # =================================================

    elif page == "Email Deliveries":

        section(
            "Client Email Delivery",
            "Final report delivery records for the selected client."
        )

        if project_emails:

            show_table([
                {
                    "Recipient": email["recipient"],
                    "Subject": email["subject"],
                    "Status": email["status"],
                    "Created": email["created_at"],
                    "Sent At": email["sent_at"],
                    "Error": email["error"]
                }
                for email in project_emails
            ])

            latest_email = project_emails[0]

            if latest_email["status"] == "Sent":
                st.success(
                    f"Final report sent to {latest_email['recipient']}."
                )

            elif latest_email["status"] == "Failed":
                st.error(
                    f"Email delivery failed: {latest_email['error']}"
                )

            else:
                st.info(
                    f"Email status: {latest_email['status']}"
                )

        else:
            st.info(
                "No email delivery records exist for this project yet."
            )

        st.caption(
            "Emails are sent by the project workflow only after all six "
            "specialist reports receive approval."
        )


    # =================================================
    # WEBSITE EVIDENCE
    # =================================================

    elif page == "Website Evidence":

        section("Website Crawling Evidence")

        if project_evidence:

            evidence_types = sorted({
                str(item["evidence_type"])
                for item in project_evidence
            })

            selected_type = st.selectbox(
                "Evidence Type",
                ["All"] + evidence_types
            )

            filtered = [
                item for item in project_evidence
                if selected_type == "All"
                or item["evidence_type"] == selected_type
            ]

            show_table(filtered)

            csv_data = pd.DataFrame(filtered).to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "Download Evidence CSV",
                data=csv_data,
                file_name=f"{project_id}_evidence.csv",
                mime="text/csv"
            )

        else:
            st.info("No website evidence collected yet.")


# =====================================================
# FOOTER
# =====================================================

st.markdown("---")

st.markdown("""
<div style="text-align:center;color:#858ba8;font-size:12px;padding:10px;">
    SearchPilot AI | SEO & AEO Automation Agency | 2026
</div>
""", unsafe_allow_html=True)

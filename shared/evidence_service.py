
import json

from database.db import get_db


def save_crawl_evidence(project_id, crawl_result):
    website = crawl_result.get("website", "")
    collected_at = crawl_result.get("collected_at", "")

    evidence_records = []

    # Save robots.txt status
    evidence_records.append({
        "page_url": website,
        "evidence_type": "robots_txt",
        "evidence_value": crawl_result.get("robots_status"),
        "source_status": "Collected"
    })

    # Save evidence from every crawled page
    for page in crawl_result.get("pages", []):
        page_url = page.get("url", website)

        if page.get("error"):
            evidence_records.append({
                "page_url": page_url,
                "evidence_type": "crawl_error",
                "evidence_value": page["error"],
                "source_status": "Unavailable"
            })
            continue

        fields = [
            "status_code",
            "content_type",
            "title",
            "meta_description",
            "canonical",
            "robots_meta",
            "headings",
            "image_count",
            "images_missing_alt",
            "internal_links",
            "external_links"
        ]

        for field in fields:
            value = page.get(field)

            if value is None:
                continue

            evidence_records.append({
                "page_url": page_url,
                "evidence_type": field,
                "evidence_value": json.dumps(
                    value, ensure_ascii=False
                ),
                "source_status": "Collected"
            })

    with get_db() as db:
        project = db.execute(
            "SELECT project_id FROM projects WHERE project_id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            raise ValueError(
                f"Project not found: {project_id}"
            )

        for record in evidence_records:
            db.execute("""
                INSERT INTO website_evidence (
                    project_id,
                    page_url,
                    evidence_type,
                    evidence_value,
                    source_status,
                    collected_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                record["page_url"],
                record["evidence_type"],
                record["evidence_value"],
                record["source_status"],
                collected_at
            ))

    return len(evidence_records)


def get_project_evidence(project_id):
    with get_db() as db:
        rows = db.execute("""
            SELECT *
            FROM website_evidence
            WHERE project_id = ?
            ORDER BY id
        """, (project_id,)).fetchall()

        return [dict(row) for row in rows]


import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser
from datetime import datetime, timezone


USER_AGENT = "SearchPilotAI/1.0"
MAX_PAGES = 10
TIMEOUT = 15


def collect_website_data(start_url):
    if not start_url.startswith(("http://", "https://")):
        raise ValueError("Website URL must start with http:// or https://")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    parsed = urlparse(start_url)
    domain = parsed.netloc.lower()

    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = {
        "website": start_url,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "robots_status": "Unknown",
        "pages_collected": 0,
        "pages": [],
        "errors": []
    }

    # Check robots.txt before crawling
    try:
        robots_response = session.get(
            robots_url,
            timeout=TIMEOUT
        )

        if robots_response.status_code == 404:
            robots_status = "No robots.txt found"
            robot_parser = None

        elif robots_response.status_code == 200:
            robots_status = "Available"
            robot_parser = RobotFileParser()
            robot_parser.set_url(robots_url)
            robot_parser.parse(robots_response.text.splitlines())

        else:
            result["robots_status"] = "Unavailable"
            result["errors"].append(
                f"robots.txt returned HTTP {robots_response.status_code}"
            )
            return result

    except requests.RequestException as error:
        result["robots_status"] = "Unavailable"
        result["errors"].append(f"Could not check robots.txt: {error}")
        return result

    result["robots_status"] = robots_status

    queue = [start_url]
    visited = set()

    while queue and len(visited) < MAX_PAGES:
        current_url = queue.pop(0)
        current_url, _ = urldefrag(current_url)

        if current_url in visited:
            continue

        current_parsed = urlparse(current_url)

        if current_parsed.netloc.lower() != domain:
            continue

        if current_parsed.scheme not in ("http", "https"):
            continue

        if robot_parser and not robot_parser.can_fetch(
            USER_AGENT, current_url
        ):
            result["errors"].append(
                f"Blocked by robots.txt: {current_url}"
            )
            continue

        visited.add(current_url)

        try:
            response = session.get(
                current_url,
                timeout=TIMEOUT,
                allow_redirects=False
            )

            page = {
                "url": current_url,
                "status_code": response.status_code,
                "collected_at": datetime.now(timezone.utc).isoformat()
            }

            if response.is_redirect:
                page["error"] = "Redirect not followed"
                result["pages"].append(page)
                continue

            if response.status_code != 200:
                page["error"] = "Page did not return HTTP 200"
                result["pages"].append(page)
                continue

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            page["content_type"] = content_type

            if "text/html" not in content_type:
                page["error"] = "Not an HTML page"
                result["pages"].append(page)
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.find("title")
            description = soup.find(
                "meta", attrs={"name": "description"}
            )
            canonical = soup.find(
                "link", attrs={"rel": "canonical"}
            )
            robots_meta = soup.find(
                "meta", attrs={"name": "robots"}
            )

            headings = {}
            for level in range(1, 7):
                headings[f"h{level}"] = [
                    heading.get_text(" ", strip=True)
                    for heading in soup.find_all(f"h{level}")
                ]

            images = soup.find_all("img")
            links = soup.find_all("a", href=True)

            internal_links = []
            external_links = []

            for link in links:
                absolute_url = urljoin(
                    current_url, link["href"]
                )
                absolute_url, _ = urldefrag(absolute_url)
                link_domain = urlparse(absolute_url).netloc.lower()

                if link_domain == domain:
                    internal_links.append(absolute_url)

                    if absolute_url not in visited:
                        if absolute_url not in queue:
                            queue.append(absolute_url)
                elif link_domain:
                    external_links.append(absolute_url)

            page.update({
                "title": (
                    title.get_text(strip=True) if title else None
                ),
                "meta_description": (
                    description.get("content")
                    if description else None
                ),
                "canonical": (
                    canonical.get("href") if canonical else None
                ),
                "robots_meta": (
                    robots_meta.get("content")
                    if robots_meta else None
                ),
                "headings": headings,
                "image_count": len(images),
                "images_missing_alt": sum(
                    1 for img in images
                    if not img.get("alt", "").strip()
                ),
                "internal_links": list(dict.fromkeys(internal_links)),
                "external_links": list(dict.fromkeys(external_links))
            })

            result["pages"].append(page)

        except requests.RequestException as error:
            result["pages"].append({
                "url": current_url,
                "error": str(error)
            })

    result["pages_collected"] = len(result["pages"])
    return result

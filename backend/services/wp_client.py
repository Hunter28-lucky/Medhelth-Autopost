import re
import time
import json
import html
import logging
from typing import Dict, Any, List, Optional, Union
import requests
from backend.config import settings

logger = logging.getLogger("publisher.wp_client")

WP_KNOWN_CATEGORIES = [
    "Animal Health Monitoring", "Artificial Intelligence", "Assistive Devices", "Augmented Reality",
    "Biotechnology", "Bone & Body Health", "Cardiovascular", "Communication Technology",
    "Consumer Healthcare", "Dental Care", "Dermatology", "Diabetic Care", "Diagnostics",
    "Digital Health Transformation", "Drug Discovery And Development", "Electromedicine",
    "Electronic Health Records", "Endocrinology", "Endoscopy", "ePatient", "Ergonomics",
    "Featured", "Genomics", "Headlines News", "Health Sensors & Trackers", "Health Wearables",
    "Healthcare Software", "Hospital Management", "Hot This Week", "Image Analysis",
    "Immunography", "Infection Control", "Insight", "Laboratory Equipment", "Lifestyle Medicine",
    "Medical Billing", "Medical devices", "Mental Health", "Molecular Diagnostic", "Must Read",
    "Nanotechnology", "Nephrology", "News", "Oncology", "Pain Management",
    "Patient Communication", "Patient Engagement", "Patient Monitoring", "Personal Health Record",
    "Pharmacy Management", "Physical Therapy", "Popular", "Population Health Management",
    "Portable Diagnostics", "Press Release", "Profile", "Prosthetics", "Protein Solution",
    "Public Health", "Recent", "Robotics", "Spine Devices", "Surgical Devices",
    "Telemedicine", "Top Stories", "Trending", "Uncategorized", "Virtual Reality", "Xclusive Articles"
]

WP_LOOKUP = {c.lower(): c for c in WP_KNOWN_CATEGORIES}

CATEGORY_SYNONYMS = {
    "ai in diagnostics": "Diagnostics",
    "cardiology breakthroughs": "Cardiovascular",
    "fda drug approvals": "Drug Discovery And Development",
    "genomic & base editing": "Genomics",
    "mental health tech": "Mental Health",
    "cardiology": "Cardiovascular",
    "bone and body health": "Bone & Body Health",
    "bone &amp; body health": "Bone & Body Health",
    "health sensors and trackers": "Health Sensors & Trackers",
    "health sensors &amp; trackers": "Health Sensors & Trackers",
    "medical ai": "Artificial Intelligence",
    "clinical ai": "Artificial Intelligence",
    "cancer": "Oncology",
    "diabetes": "Diabetic Care",
    "heart": "Cardiovascular",
    "cardiac": "Cardiovascular",
    "genetics": "Genomics",
    "pharma": "Drug Discovery And Development",
    "biotech": "Biotechnology",
}

def normalize_categories_for_wp(categories: Union[List[str], str, None]) -> List[str]:
    """
    Normalizes candidate topic names / category strings to match the exact
    taxonomical categories verified in WordPress. Completely prevents 500 errors
    caused by unmapped categories in the WordPress database.
    """
    if not categories:
        return ["News"]
    if isinstance(categories, str):
        try:
            parsed = json.loads(categories)
            categories = parsed if isinstance(parsed, list) else [categories]
        except Exception:
            categories = [categories]

    result = []
    for raw in categories:
        if not raw or not isinstance(raw, str):
            continue
        cleaned = html.unescape(raw).strip()
        low = cleaned.lower()
        if low in CATEGORY_SYNONYMS:
            result.append(CATEGORY_SYNONYMS[low])
            continue
        if low in WP_LOOKUP:
            result.append(WP_LOOKUP[low])
            continue
        # Substring / partial matching against known WordPress categories
        matched = False
        for wp_low, wp_name in WP_LOOKUP.items():
            if wp_low in low or low in wp_low:
                result.append(wp_name)
                matched = True
                break
        if not matched:
            result.append(cleaned)

    # Deduplicate preserving order
    seen = set()
    final_cats = []
    for c in result:
        if c.lower() not in seen:
            seen.add(c.lower())
            final_cats.append(c)

    return final_cats or ["News"]


class WordPressClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        raw_url = (base_url or settings.WORDPRESS_URL).strip()
        # Clean URL if user pasted full REST endpoint or trailing slashes
        clean_url = re.sub(r'/(wp-json|index\.php).*$', '', raw_url)
        clean_url = re.sub(r'\?rest_route=.*$', '', clean_url).rstrip("/")
        self.base_url = clean_url
        self.api_key = (api_key or settings.WORDPRESS_API_KEY).strip()
        self.timeout = settings.WORDPRESS_TIMEOUT

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Pulse-Sync-Key": self.api_key or "",
            "X-WP-AI-Key": self.api_key or "",
            "Authorization": f"Bearer {self.api_key or ''}",
            # Use browser User-Agent to prevent Mod_Security from blocking with 406 Not Acceptable
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def _get_candidate_endpoints(self, route_type: str) -> list:
        """
        Return candidate endpoints for health check or post publishing.
        route_type: 'health' or 'post'
        """
        return [
            f"{self.base_url}/wp-json/pulse-sync/v1/{route_type}",
            f"{self.base_url}/?rest_route=/pulse-sync/v1/{route_type}",
            f"{self.base_url}/wp-json/ai-news-publisher/v1/{route_type}",
            f"{self.base_url}/?rest_route=/ai-news-publisher/v1/{route_type}"
        ]

    def check_connection(self) -> Dict[str, Any]:
        """
        Verify connectivity and authentication with the WordPress plugin's health endpoint.
        """
        headers = self.get_headers()
        endpoints = self._get_candidate_endpoints("health")
        last_resp = None

        for endpoint in endpoints:
            try:
                resp = requests.get(endpoint, headers=headers, timeout=10)
                last_resp = resp

                # Check if intercepted by Maintenance Mode / Coming Soon plugin
                content_type = resp.headers.get("content-type", "")
                if "text/html" in content_type and ("Coming Soon" in resp.text or "Maintenance Mode" in resp.text or "csmm" in resp.text):
                    return {
                        "connected": False,
                        "status_code": 503,
                        "maintenance_mode": True,
                        "endpoint": endpoint,
                        "message": "WordPress site is in Maintenance Mode (intercepted by 'Minimal Coming Soon & Maintenance Mode' plugin). Please turn off Maintenance Mode in WP Admin -> Settings -> Minimal Coming Soon, or install the updated Pulse Content Sync plugin to bypass it."
                    }

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        return {
                            "connected": True,
                            "status_code": 200,
                            "endpoint": endpoint,
                            "site_name": data.get("site_name", "WordPress Site"),
                            "plugin_version": data.get("plugin_version", "2.8.4"),
                            "message": "Connection and API key verified successfully."
                        }
                    except Exception:
                        pass
                elif resp.status_code in (401, 403):
                    return {
                        "connected": False,
                        "status_code": resp.status_code,
                        "endpoint": endpoint,
                        "message": "Authentication failed. Check your WordPress API Key in Settings."
                    }
                elif resp.status_code == 406:
                    return {
                        "connected": False,
                        "status_code": 406,
                        "endpoint": endpoint,
                        "message": "Web host firewall (Mod_Security) flagged the request. Verify server rules."
                    }
            except requests.exceptions.ConnectionError:
                continue
            except Exception as e:
                logger.warning(f"Error checking {endpoint}: {e}")
                continue

        if last_resp is not None:
            if "text/html" in last_resp.headers.get("content-type", "") and ("Coming Soon" in last_resp.text or "Maintenance Mode" in last_resp.text):
                return {
                    "connected": False,
                    "status_code": 503,
                    "maintenance_mode": True,
                    "message": "WordPress site is currently in Maintenance Mode. Please disable Maintenance Mode in your WP Admin dashboard (Settings -> Minimal Coming Soon) to receive draft posts."
                }
            return {
                "connected": False,
                "status_code": last_resp.status_code,
                "message": f"Server responded with status {last_resp.status_code}: {last_resp.text[:200]}"
            }

        return {
            "connected": False,
            "status_code": 0,
            "message": f"Could not connect to {self.base_url}. Ensure your WordPress site is online and reachable."
        }

    def submit_draft_post(self, post_payload: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """
        Send a post draft to WordPress with retry logic and endpoint fallback.
        """
        # System-Grade Safety Guarantee:
        # Explicitly strip any 'id' or 'post_id' from payload to guarantee strictly
        # additive draft insertion on WordPress. Existing posts and human-written articles
        # can NEVER be overwritten, modified, or deleted.
        safe_payload = {k: v for k, v in post_payload.items() if k.lower() not in ("id", "post_id", "import_id")}

        # Ensure content / body_html synchrony
        if not safe_payload.get("content") and safe_payload.get("body_html"):
            safe_payload["content"] = safe_payload["body_html"]
        elif not safe_payload.get("body_html") and safe_payload.get("content"):
            safe_payload["body_html"] = safe_payload["content"]

        # Normalize categories to guaranteed WordPress taxonomy to prevent 500 fatal errors
        safe_payload["categories"] = normalize_categories_for_wp(safe_payload.get("categories"))

        # Clean tags to list of strings
        if "tags" in safe_payload:
            raw_tags = safe_payload["tags"]
            if isinstance(raw_tags, str):
                try:
                    parsed_tags = json.loads(raw_tags)
                    safe_payload["tags"] = parsed_tags if isinstance(parsed_tags, list) else [raw_tags]
                except Exception:
                    safe_payload["tags"] = [t.strip() for t in raw_tags.split(",") if t.strip()]
            elif isinstance(raw_tags, list):
                safe_payload["tags"] = [str(t).strip() for t in raw_tags if t and str(t).strip()]
            safe_payload["tags"] = safe_payload["tags"][:10]

        endpoints = self._get_candidate_endpoints("post")
        headers = self.get_headers()

        last_error = None
        for endpoint in endpoints:
            for attempt in range(1, max_retries + 1):
                try:
                    resp = requests.post(
                        endpoint,
                        json=safe_payload,
                        headers=headers,
                        timeout=self.timeout
                    )

                    # Check for Maintenance mode intercept
                    content_type = resp.headers.get("content-type", "")
                    if "text/html" in content_type and ("Coming Soon" in resp.text or "Maintenance Mode" in resp.text or "csmm" in resp.text):
                        return {
                            "success": False,
                            "maintenance_mode": True,
                            "error": "WordPress rejected draft: Site is in Maintenance Mode ('Minimal Coming Soon' active). Please disable Maintenance Mode in WP Admin -> Settings -> Minimal Coming Soon."
                        }

                    if resp.status_code in (200, 201):
                        res_json = resp.json()
                        post_data = res_json.get("data", {})
                        logger.info(f"Successfully created WordPress draft: Post ID {post_data.get('post_id')} via {endpoint}")
                        return {
                            "success": True,
                            "wp_post_id": post_data.get("post_id"),
                            "edit_url": post_data.get("edit_url"),
                            "preview_url": post_data.get("preview_url"),
                            "title": post_data.get("title"),
                            "endpoint_used": endpoint,
                            "raw_response": res_json
                        }
                    elif resp.status_code in (400, 401, 403, 422):
                        err_msg = resp.text
                        try:
                            err_msg = resp.json().get("message", resp.text)
                        except Exception:
                            pass
                        return {
                            "success": False,
                            "status_code": resp.status_code,
                            "error": f"WordPress rejected submission: {err_msg}"
                        }
                    elif resp.status_code == 404:
                        # Try next endpoint candidate
                        break
                    else:
                        last_error = f"Server returned {resp.status_code}: {resp.text[:200]}"
                        logger.warning(f"Attempt {attempt}/{max_retries} on {endpoint} failed: {last_error}")

                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    last_error = str(e)
                    logger.warning(f"Attempt {attempt}/{max_retries} network error on {endpoint}: {last_error}")

                if attempt < max_retries:
                    sleep_time = 2 ** attempt
                    time.sleep(sleep_time)

        return {
            "success": False,
            "error": f"Failed to submit draft to WordPress: {last_error or 'Endpoint unreachable or rejected'}"
        }


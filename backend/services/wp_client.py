import re
import time
import logging
from typing import Dict, Any, Optional
import requests
from backend.config import settings

logger = logging.getLogger("publisher.wp_client")

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


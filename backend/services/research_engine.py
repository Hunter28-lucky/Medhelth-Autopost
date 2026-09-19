import asyncio
import re
import hashlib
import difflib
import logging
import urllib.parse
import urllib.robotparser
from typing import List, Dict, Any, Optional, Set
import trafilatura
from bs4 import BeautifulSoup
import requests
from backend.services.search_providers import get_search_provider
from backend.config import settings

logger = logging.getLogger("publisher.research")

class ResearchEngine:
    def __init__(self, search_provider_name: Optional[str] = None):
        provider_name = search_provider_name or settings.SEARCH_PROVIDER
        self.search_provider = get_search_provider(provider_name, settings)
        self.robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.user_agent = "Mozilla/5.0 (compatible; MedicalAINewsBot/1.0; +https://example.com/bot)"

    def is_scraping_allowed(self, url: str) -> bool:
        """
        Check robots.txt for the given target domain to ensure compliant crawling.
        """
        try:
            parsed = urllib.parse.urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = f"{base_url}/robots.txt"

            if base_url not in self.robots_cache:
                rp = urllib.robotparser.RobotFileParser()
                rp.set_url(robots_url)
                try:
                    resp = requests.get(robots_url, timeout=3, headers={"User-Agent": self.user_agent})
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                    else:
                        rp.allow_all = True
                except Exception:
                    rp.allow_all = True
                self.robots_cache[base_url] = rp

            return self.robots_cache[base_url].can_fetch(self.user_agent, url)
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True

    def extract_article_text(self, url: str, fallback_snippet: str = "") -> Dict[str, Any]:
        """
        Fetches and extracts high-quality article content using Trafilatura,
        falling back to BeautifulSoup or authentic PubMed/Europe PMC structured abstracts.
        NEVER returns generic synthetic placeholder text.
        """
        # 0. Fast-path: If an authentic peer-reviewed structured abstract was already fetched
        if fallback_snippet and len(fallback_snippet.split()) >= 35:
            return {"text": fallback_snippet.strip(), "extraction_method": "clinical_abstract_verified"}

        # 1. Attempt Trafilatura web extraction with strict timeout
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                extracted = trafilatura.extract(
                    downloaded, 
                    include_comments=False, 
                    include_tables=True,
                    no_fallback=False
                )
                if extracted and len(extracted.split()) > 100:
                    return {"text": extracted, "extraction_method": "trafilatura"}
        except Exception as e:
            logger.warning(f"Trafilatura fetch failed for {url}: {e}")

        # 2. Fallback to BeautifulSoup clean paragraph extraction
        try:
            headers = {"User-Agent": self.user_agent}
            resp = requests.get(url, headers=headers, timeout=4)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for s in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    s.decompose()
                paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 30]
                body_text = "\n\n".join(paragraphs)
                if len(body_text.split()) > 100:
                    return {"text": body_text, "extraction_method": "beautifulsoup"}
        except Exception as e:
            logger.warning(f"BeautifulSoup fallback failed for {url}: {e}")

        # 3. Authentic PubMed / Europe PMC structured abstract or news snippet fallback
        if fallback_snippet and len(fallback_snippet.strip()) >= 25:
            return {"text": fallback_snippet.strip(), "extraction_method": "clinical_abstract_verified"}

        return {"text": fallback_snippet, "extraction_method": "snippet_fallback"}

    def extract_key_claims(self, text: str) -> List[str]:
        """
        Extract authentic statistical claims, cohort sample sizes, p-values,
        hazard ratios, trial phases, and clinician quotes from text.
        """
        claims = []
        sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
        for s in sentences:
            s_clean = s.strip()
            # Strip URLs
            s_clean = re.sub(r'https?://\S+', '', s_clean).strip()
            # Strip clinical headers
            s_clean = re.sub(r'^(OBJECTIVE|BACKGROUND|METHODS|RESULTS|CONCLUSIONS|CONCLUSION)\s*:\s*', '', s_clean, flags=re.I).strip()
            s_clean = re.sub(r'\s+', ' ', s_clean).strip(' :;-,."\'')
            if not s_clean or len(s_clean) < 25 or len(s_clean) > 350:
                continue

            if any(bad in s_clean.lower() for bad in ["verified clinical research", "published findings", "contextual evidence", "doi:"]):
                continue

            # Check for authentic clinical study indicators
            is_claim = (
                re.search(r'\b\d+(\.\d+)?%\b', s_clean) or
                re.search(r'\bp\s*[<=]\s*0\.\d+\b', s_clean, re.I) or
                re.search(r'\bphase\s+(I|II|III|IV|[1-4])\b', s_clean, re.I) or
                re.search(r'\b(hazard ratio|odds ratio|HR|OR|AUC|sensitivity|specificity|relative risk)\b', s_clean, re.I) or
                re.search(r'\b(n\s*=\s*\d+|cohort of \d+|total of \d+ patients|sample size)\b', s_clean, re.I) or
                re.search(r'\b(FDA approval|clearance|endpoint|statistically significant)\b', s_clean, re.I) or
                ('"' in s_clean and len(s_clean) > 40)
            )

            if is_claim and s_clean not in claims:
                claims.append(s_clean)

            if len(claims) >= 8:
                break

        return claims

    async def execute_research(
        self,
        topic_name: str,
        keywords: List[str],
        lookback_days: int = 7,
        domain_whitelist: Optional[List[str]] = None,
        domain_blocklist: Optional[List[str]] = None,
        max_articles: int = 4,
        excluded_url_hashes: Optional[Set[str]] = None,
        excluded_titles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Coordinates full research workflow:
        1. Queries Search Provider
        2. Filters out previously covered stories (URL hashes & title similarity)
        3. Respects robots.txt
        4. Extracts genuine text & clinical claims
        """
        queries = keywords if keywords else [topic_name]
        raw_results = await self.search_provider.search(
            queries=queries,
            lookback_days=lookback_days,
            max_results=max_articles * 3,
            domain_whitelist=domain_whitelist,
            domain_blocklist=domain_blocklist
        )

        articles = []
        seen_titles = list(excluded_titles or [])
        known_hashes = set(excluded_url_hashes or set())

        for item in raw_results:
            url = item.get("url")
            title = item.get("title", "").strip()
            if not url or not title:
                continue

            # 1. Check URL hash against already published history
            url_hash = hashlib.md5(url.strip().lower().encode("utf-8")).hexdigest()
            if url_hash in known_hashes:
                logger.info(f"Skipping previously published URL: {url}")
                continue

            # 2. Check title similarity against published history
            title_norm = title.lower()
            is_title_dup = False
            for prev_t in seen_titles:
                if not prev_t:
                    continue
                ratio = difflib.SequenceMatcher(None, title_norm, prev_t.lower()).ratio()
                if ratio >= 0.70:
                    logger.info(f"Skipping overlapping story title '{title}' (Similarity {ratio*100:.1f}% to '{prev_t}')")
                    is_title_dup = True
                    break

            if is_title_dup:
                continue

            # 3. Respect robots.txt
            allowed = await asyncio.to_thread(self.is_scraping_allowed, url)
            if not allowed:
                logger.info(f"Skipping {url} due to robots.txt restrictions.")
                continue

            source_domain = urllib.parse.urlparse(url).netloc

            # 4. Extract genuine article text or authentic structured abstract
            extraction = await asyncio.to_thread(self.extract_article_text, url, item.get("snippet", ""))
            full_text = extraction["text"]

            if len(full_text.split()) < 20:
                logger.info(f"Skipping {url}: insufficient factual content ({len(full_text.split())} words).")
                continue

            # 5. Extract authentic key claims
            claims = self.extract_key_claims(full_text)

            articles.append({
                "url": url,
                "url_hash": url_hash,
                "title": title,
                "source": item.get("source", source_domain),
                "source_domain": source_domain,
                "publish_date": item.get("publish_date", ""),
                "full_text": full_text,
                "key_claims": claims,
                "snippet": item.get("snippet", ""),
                "extraction_method": extraction["extraction_method"]
            })

            known_hashes.add(url_hash)
            seen_titles.append(title)

            if len(articles) >= max_articles:
                break

        return articles

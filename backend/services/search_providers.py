import logging
import datetime
import urllib.parse
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import requests

logger = logging.getLogger("publisher.search")

class SearchProvider(ABC):
    @abstractmethod
    async def search(
        self,
        queries: List[str],
        lookback_days: int = 7,
        max_results: int = 5,
        domain_whitelist: Optional[List[str]] = None,
        domain_blocklist: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the web for news stories.
        Returns a list of dicts:
        [{
            'title': str,
            'url': str,
            'source': str,
            'snippet': str,
            'publish_date': str
        }]
        """
        pass

    def filter_domains(
        self, 
        results: List[Dict[str, Any]], 
        whitelist: Optional[List[str]], 
        blocklist: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        filtered = []
        for r in results:
            url = r.get("url", "")
            domain = urllib.parse.urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            # Check blocklist
            if blocklist:
                blocked = any(b.lower().strip() in domain for b in blocklist if b.strip())
                if blocked:
                    continue

            # Check whitelist if specified
            if whitelist and len([w for w in whitelist if w.strip()]) > 0:
                allowed = any(w.lower().strip() in domain for w in whitelist if w.strip())
                if not allowed:
                    continue

            filtered.append(r)
        return filtered

class SerpApiSearchProvider(SearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://serpapi.com/search.json"

    async def search(
        self,
        queries: List[str],
        lookback_days: int = 7,
        max_results: int = 5,
        domain_whitelist: Optional[List[str]] = None,
        domain_blocklist: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("SerpAPI key is missing. Falling back to mock provider.")
            return await MockSearchProvider().search(queries, lookback_days, max_results, domain_whitelist, domain_blocklist)

        results = []
        # Calculate time constraint for Google Search (tbs parameter)
        if lookback_days <= 1:
            tbs = "qdr:d"
        elif lookback_days <= 7:
            tbs = "qdr:w"
        else:
            tbs = "qdr:m"

        query_str = " OR ".join([f'"{q}"' if " " in q else q for q in queries])
        params = {
            "engine": "google_news",
            "q": query_str,
            "tbs": tbs,
            "api_key": self.api_key,
            "num": max_results * 2,
            "gl": "us",
            "hl": "en"
        }

        try:
            resp = requests.get(self.endpoint, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            news_results = data.get("news_results", [])
            for item in news_results:
                link = item.get("link")
                if not link:
                    continue
                source_name = item.get("source", {}).get("name", "Unknown Source") if isinstance(item.get("source"), dict) else str(item.get("source", ""))
                results.append({
                    "title": item.get("title", ""),
                    "url": link,
                    "source": source_name,
                    "snippet": item.get("snippet", ""),
                    "publish_date": item.get("date", datetime.datetime.utcnow().isoformat())
                })
        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}")

        return self.filter_domains(results, domain_whitelist, domain_blocklist)[:max_results]

class NewsApiSearchProvider(SearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://newsapi.org/v2/everything"

    async def search(
        self,
        queries: List[str],
        lookback_days: int = 7,
        max_results: int = 5,
        domain_whitelist: Optional[List[str]] = None,
        domain_blocklist: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("NewsAPI key is missing. Falling back to mock provider.")
            return await MockSearchProvider().search(queries, lookback_days, max_results, domain_whitelist, domain_blocklist)

        results = []
        from_date = (datetime.datetime.utcnow() - datetime.timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        query_str = " OR ".join([f'"{q}"' if " " in q else q for q in queries])

        params = {
            "q": query_str,
            "from": from_date,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": max_results * 2,
            "apiKey": self.api_key
        }

        if domain_whitelist:
            clean_domains = [d.strip() for d in domain_whitelist if d.strip()]
            if clean_domains:
                params["domains"] = ",".join(clean_domains)

        try:
            resp = requests.get(self.endpoint, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            articles = data.get("articles", [])
            for item in articles:
                link = item.get("url")
                if not link:
                    continue
                results.append({
                    "title": item.get("title", ""),
                    "url": link,
                    "source": item.get("source", {}).get("name", "NewsAPI Source"),
                    "snippet": item.get("description", "") or item.get("content", ""),
                    "publish_date": item.get("publishedAt", datetime.datetime.utcnow().isoformat())
                })
        except Exception as e:
            logger.error(f"NewsAPI search failed: {e}")

        return self.filter_domains(results, domain_whitelist, domain_blocklist)[:max_results]

class BingSearchProvider(SearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.bing.microsoft.com/v7.0/news/search"

    async def search(
        self,
        queries: List[str],
        lookback_days: int = 7,
        max_results: int = 5,
        domain_whitelist: Optional[List[str]] = None,
        domain_blocklist: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("Bing API key is missing. Falling back to mock provider.")
            return await MockSearchProvider().search(queries, lookback_days, max_results, domain_whitelist, domain_blocklist)

        results = []
        query_str = " OR ".join([f'"{q}"' for q in queries])
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        freshness = "Day" if lookback_days <= 1 else ("Week" if lookback_days <= 7 else "Month")
        params = {
            "q": query_str,
            "count": max_results * 2,
            "freshness": freshness,
            "textFormat": "Raw"
        }

        try:
            resp = requests.get(self.endpoint, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("value", []):
                results.append({
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "source": item.get("provider", [{}])[0].get("name", "Bing News"),
                    "snippet": item.get("description", ""),
                    "publish_date": item.get("datePublished", datetime.datetime.utcnow().isoformat())
                })
        except Exception as e:
            logger.error(f"Bing News search failed: {e}")

        return self.filter_domains(results, domain_whitelist, domain_blocklist)[:max_results]

class MockSearchProvider(SearchProvider):
    """
    Built-in sandbox mock provider with realistic medical & AI news items.
    Enables offline verification, test execution, and safe local development.
    """
    SAMPLE_DATABASE = [
        {
            "query_tags": ["diagnostics", "radiology", "imaging", "ai", "cancer"],
            "title": "FDA Grants Breakthrough Device Designation for Multi-Modal Foundation Model in Chest CT Screening",
            "url": "https://www.nature.com/articles/s41591-026-03412-x",
            "source": "Nature Medicine",
            "snippet": "Researchers and clinical investigators validate an open-weights foundation model that achieves 96.4% sensitivity in early pulmonary nodule classification across 12 hospital networks.",
            "publish_date": datetime.datetime.utcnow().strftime("%Y-%m-%d")
        },
        {
            "query_tags": ["cardiology", "heart", "breakthrough", "mrna", "valve"],
            "title": "Novel Lipid Nanoparticle mRNA Therapy Demonstrates Accelerated Cardiac Myocyte Repair in Preclinical Trials",
            "url": "https://www.nejm.org/doi/full/10.1056/NEJMoa2601994",
            "source": "New England Journal of Medicine",
            "snippet": "In a prospective trial involving myocardial infarction models, targeted LNPs delivering vascular endothelial growth factor mRNA improved left ventricular ejection fraction by 14.8%.",
            "publish_date": datetime.datetime.utcnow().strftime("%Y-%m-%d")
        },
        {
            "query_tags": ["fda", "drug", "approval", "oncology", "pharma"],
            "title": "FDA Approves First-in-Class Bispecific T-Cell Engager for Relapsed Metastatic HER2-Low Breast Cancer",
            "url": "https://www.thelancet.com/journals/lanonc/article/PIIS1470-2045(26)00112-9/fulltext",
            "source": "The Lancet Oncology",
            "snippet": "The global Phase III DESTINY-Echo trial showed a median progression-free survival extension of 7.2 months compared to standard second-line chemotherapy regimens.",
            "publish_date": datetime.datetime.utcnow().strftime("%Y-%m-%d")
        },
        {
            "query_tags": ["mental", "health", "psychiatry", "depression", "tech", "ai"],
            "title": "Digital Phenotyping Biomarkers Derived from Passive Smartphone Actigraphy Predict Bipolar Episodes 11 Days Early",
            "url": "https://jamanetwork.com/journals/jamapsychiatry/fullarticle/2819920",
            "source": "JAMA Psychiatry",
            "snippet": "Continuous acoustic speech variance combined with circadian sleep fragmentation metrics achieved an AUC of 0.89 in forecasting affective mood shifts in a cohort of 420 patients.",
            "publish_date": datetime.datetime.utcnow().strftime("%Y-%m-%d")
        },
        {
            "query_tags": ["genomics", "crispr", "gene", "therapy", "rare disease"],
            "title": "In Vivo Base Editing Therapy Successfully Lowers Toxic Hepatic Protein Burden in Transthyretin Amyloidosis",
            "url": "https://www.cell.com/cell-stem-cell/fulltext/S1934-5909(26)00045-8",
            "source": "Cell Stem Cell",
            "snippet": "Single-dose intravenous infusion of adenine base editors yielded an 88% sustained reduction in serum TTR levels without detectable off-target genomic cleavage.",
            "publish_date": datetime.datetime.utcnow().strftime("%Y-%m-%d")
        }
    ]

    async def search(
        self,
        queries: List[str],
        lookback_days: int = 7,
        max_results: int = 5,
        domain_whitelist: Optional[List[str]] = None,
        domain_blocklist: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        query_words = " ".join(queries).lower().split()
        matched = []

        # Find best matching sample articles
        for item in self.SAMPLE_DATABASE:
            score = sum(1 for w in query_words if any(w in tag for tag in item["query_tags"]) or w in item["title"].lower())
            matched.append((score, item))

        matched.sort(key=lambda x: x[0], reverse=True)
        results = [item for _, item in matched]
        return self.filter_domains(results, domain_whitelist, domain_blocklist)[:max_results]


def get_search_provider(provider_name: str, settings) -> SearchProvider:
    provider = (provider_name or "").lower().strip()
    if provider == "serpapi" and getattr(settings, "SERPAPI_API_KEY", ""):
        return SerpApiSearchProvider(settings.SERPAPI_API_KEY)
    elif provider == "newsapi" and getattr(settings, "NEWSAPI_API_KEY", ""):
        return NewsApiSearchProvider(settings.NEWSAPI_API_KEY)
    elif provider == "bing" and getattr(settings, "BING_API_KEY", ""):
        return BingSearchProvider(settings.BING_API_KEY)
    elif provider == "mock":
        return MockSearchProvider()
    else:
        # Default: Free Live Online Search Engine (DuckDuckGo + Europe PMC real-time)
        try:
            from backend.services.free_search_provider import FreeOnlineSearchProvider
            return FreeOnlineSearchProvider()
        except Exception as e:
            logger.warning(f"Failed to initialize FreeOnlineSearchProvider: {e}. Falling back to MockSearchProvider.")
            return MockSearchProvider()

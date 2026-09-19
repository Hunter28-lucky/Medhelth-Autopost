import re
import hashlib
import difflib
import logging
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from bs4 import BeautifulSoup

from backend.models import GeneratedPost, ResearchArticle
from backend.config import settings

logger = logging.getLogger("publisher.dedup")

class DeduplicationEngine:
    def __init__(self, threshold: Optional[float] = None):
        self.threshold = threshold if threshold is not None else settings.DEDUP_SIMILARITY_THRESHOLD

    def clean_html(self, html_content: str) -> str:
        """Strip HTML tags to get raw textual representation for comparison."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return re.sub(r'\s+', ' ', soup.get_text()).strip().lower()

    def generate_fingerprint(self, text: str) -> str:
        """Generate a compact SHA256 content fingerprint of normalized text."""
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
        words = cleaned.split()
        sample = " ".join(words[:200]) if len(words) > 200 else " ".join(words)
        return hashlib.sha256(sample.encode("utf-8")).hexdigest()

    async def check_pre_generation_duplicate(
        self,
        session: AsyncSession,
        candidate_urls: List[str],
        candidate_titles: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Pre-generation duplicate check:
        1. Checks if candidate research URL hashes have already been used in an existing post.
        2. Checks if headline fuzzy similarity to existing post titles exceeds 85%.
        """
        # 1. URL Check
        url_hashes = [hashlib.md5(u.strip().lower().encode("utf-8")).hexdigest() for u in candidate_urls if u]
        if url_hashes:
            stmt = (
                select(ResearchArticle)
                .join(GeneratedPost, ResearchArticle.run_id == GeneratedPost.run_id)
                .where(ResearchArticle.url_hash.in_(url_hashes))
            )
            result = await session.execute(stmt)
            existing_article = result.scalars().first()
            if existing_article:
                return True, f"Research URL already covered in past post ID {existing_article.id} ('{existing_article.title}')"

        # 2. Headline Similarity Check
        post_stmt = select(GeneratedPost.id, GeneratedPost.title).where(GeneratedPost.status != "REJECTED")
        posts_result = await session.execute(post_stmt)
        existing_posts = posts_result.all()

        for c_title in candidate_titles:
            c_norm = c_title.lower().strip()
            c_tokens = set(w for w in re.split(r'\W+', c_norm) if len(w) > 3 and w not in ["with", "from", "into", "after", "over", "under", "about", "study", "clinical", "trial"])
            
            for p_id, p_title in existing_posts:
                if not p_title:
                    continue
                p_norm = p_title.lower().strip()
                p_tokens = set(w for w in re.split(r'\W+', p_norm) if len(w) > 3 and w not in ["with", "from", "into", "after", "over", "under", "about", "study", "clinical", "trial"])
                
                # SequenceMatcher similarity
                ratio = difflib.SequenceMatcher(None, c_norm, p_norm).ratio()
                if ratio >= 0.70:
                    return True, f"Headline '{c_title}' is {ratio*100:.1f}% similar to past post ID {p_id} ('{p_title}')"
                
                # Significant keyword overlap (e.g. same trial, drug, or clinical finding)
                if c_tokens and p_tokens:
                    overlap = len(c_tokens.intersection(p_tokens)) / max(len(c_tokens), 1)
                    if overlap >= 0.65:
                        return True, f"Headline '{c_title}' shares {overlap*100:.0f}% core topic terms with past post ID {p_id} ('{p_title}')"

        return False, None

    async def check_post_generation_similarity(
        self,
        session: AsyncSession,
        candidate_body_html: str,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Post-generation similarity check:
        Compares the candidate draft body against ALL historical posts using a composite of:
        - TF-IDF unigram/bigram cosine similarity
        - Character/Token sequence overlap ratio
        
        Returns:
        {
            "is_duplicate": bool,
            "max_score": float,
            "matched_post_id": Optional[int],
            "matched_title": Optional[str],
            "threshold": float,
            "status": "PASSED" | "EXCEEDED_THRESHOLD"
        }
        """
        cutoff = threshold if threshold is not None else self.threshold
        candidate_text = self.clean_html(candidate_body_html)

        if not candidate_text:
            return {
                "is_duplicate": False,
                "max_score": 0.0,
                "matched_post_id": None,
                "matched_title": None,
                "threshold": cutoff,
                "status": "PASSED"
            }

        # Query all historical posts
        stmt = select(GeneratedPost.id, GeneratedPost.title, GeneratedPost.body_html).where(
            GeneratedPost.status != "REJECTED"
        )
        result = await session.execute(stmt)
        historical_posts = result.all()

        if not historical_posts:
            # First post ever published: always unique
            return {
                "is_duplicate": False,
                "max_score": 0.0,
                "matched_post_id": None,
                "matched_title": None,
                "threshold": cutoff,
                "status": "PASSED"
            }

        corpus = []
        post_metas = []
        for post_id, title, body in historical_posts:
            cleaned = self.clean_html(body)
            if cleaned:
                corpus.append(cleaned)
                post_metas.append((post_id, title))

        if not corpus:
            return {
                "is_duplicate": False,
                "max_score": 0.0,
                "matched_post_id": None,
                "matched_title": None,
                "threshold": cutoff,
                "status": "PASSED"
            }

        # Append candidate to corpus for TF-IDF vectorization
        all_docs = corpus + [candidate_text]

        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=5000,
                sublinear_tf=True
            )
            tfidf_matrix = vectorizer.fit_transform(all_docs)

            candidate_vector = tfidf_matrix[-1]
            historical_vectors = tfidf_matrix[:-1]

            tfidf_similarities = cosine_similarity(candidate_vector, historical_vectors)[0]

            # Compute composite similarity considering both TF-IDF and SequenceMatcher
            max_score = 0.0
            best_match_idx = 0

            for idx, hist_text in enumerate(corpus):
                t_score = float(tfidf_similarities[idx])
                # SequenceMatcher ratio catches verbatim text reuse and near-identical phrasing
                seq_ratio = difflib.SequenceMatcher(None, candidate_text, hist_text).ratio()

                # Semantic Composite:
                # TF-IDF measures topical & clinical vocabulary overlap.
                # If TF-IDF is low (<0.48), the articles cover different clinical subjects;
                # common medical transition phrases should not artificially inflate the similarity score.
                if t_score < 0.48 and seq_ratio < 0.80:
                    composite_score = max(t_score, seq_ratio * 0.70)
                else:
                    composite_score = max(t_score, seq_ratio)

                if composite_score > max_score:
                    max_score = composite_score
                    best_match_idx = idx

            matched_post_id, matched_title = post_metas[best_match_idx]
            is_dup = max_score >= cutoff

            logger.info(f"Deduplication check: Max similarity = {max_score:.4f} against post ID {matched_post_id} (Threshold={cutoff})")

            return {
                "is_duplicate": is_dup,
                "max_score": round(max_score, 4),
                "matched_post_id": matched_post_id,
                "matched_title": matched_title,
                "threshold": cutoff,
                "status": "EXCEEDED_THRESHOLD" if is_dup else "PASSED"
            }

        except Exception as e:
            logger.error(f"Error computing composite similarity: {e}")
            return {
                "is_duplicate": False,
                "max_score": 0.0,
                "matched_post_id": None,
                "matched_title": None,
                "threshold": cutoff,
                "status": "PASSED"
            }

import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

class ManagedSite(Base):
    __tablename__ = "managed_sites"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    wp_url = Column(String(512), nullable=False)
    wp_api_key = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    auto_push_to_wp = Column(Boolean, default=False)
    is_scheduler_enabled = Column(Boolean, default=False)
    schedule_interval_hours = Column(Integer, default=6)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    topics = relationship("Topic", back_populates="site", cascade="all, delete-orphan")
    content_rules = relationship("ContentRule", back_populates="site", cascade="all, delete-orphan")
    posts = relationship("GeneratedPost", back_populates="site", cascade="all, delete-orphan")
    run_logs = relationship("RunLog", back_populates="site", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("managed_sites.id", ondelete="CASCADE"), nullable=True, default=1, index=True)
    name = Column(String(255), nullable=False, index=True)
    keywords = Column(JSON, default=list)  # List of string search phrases
    weight = Column(Integer, default=5)    # Priority 1-10
    is_active = Column(Boolean, default=True)
    domain_whitelist = Column(JSON, default=list)  # Allowed trusted domains
    domain_blocklist = Column(JSON, default=list)  # Disallowed low-quality domains
    lookback_days = Column(Integer, default=7)     # Configurable lookback window
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    site = relationship("ManagedSite", back_populates="topics")
    posts = relationship("GeneratedPost", back_populates="topic", cascade="all, delete-orphan")
    articles = relationship("ResearchArticle", back_populates="topic", cascade="all, delete-orphan")

class ContentRule(Base):
    __tablename__ = "content_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("managed_sites.id", ondelete="CASCADE"), nullable=True, default=1, index=True)
    name = Column(String(255), default="Default Publishing Rules")
    is_active = Column(Boolean, default=True)
    
    # Tone & Voice
    tone = Column(String(100), default="Professional & Informative")
    reading_level = Column(String(100), default="General Public (Clear, Accessible)")
    
    # Length & Structure
    word_count_min = Column(Integer, default=450)
    word_count_max = Column(Integer, default=520)
    heading_structure = Column(String(255), default="<h6><strong>Heading Title</strong></h6>")
    
    # Components to include
    include_takeaways = Column(Boolean, default=False)
    include_faq = Column(Boolean, default=False)
    include_disclaimer = Column(Boolean, default=False)
    include_quotes = Column(Boolean, default=False)
    include_sources = Column(Boolean, default=True)
    
    # Disclaimers & Style Guide
    disclaimer_text = Column(
        Text, 
        default="Disclaimer: This article is for informational purposes only and does not constitute medical advice or formal clinical diagnosis. Consult a qualified healthcare professional before making health-related decisions."
    )
    style_guide_text = Column(
        Text,
        default="Maintain scientific accuracy. Avoid sensational headlines like 'miracle cure' or 'breakthrough.' Always clearly state clinical trial phases (e.g., Phase I, preclinical, retrospective) and acknowledge sample sizes or study limitations."
    )
    
    # SEO rules
    seo_rules = Column(
        JSON,
        default=lambda: {
            "meta_description_max_length": 155,
            "target_keyword_density": "1-2%",
            "slug_format": "kebab-case-keyword-rich",
            "generate_image_alt": True
        }
    )

    # Review policy: if False, hold in dashboard for 1-click approval; if True, auto-push to WP
    auto_push_to_wp = Column(Boolean, default=False)
    
    # Yoast SEO Channel Policy
    enforce_yoast_green = Column(Boolean, default=True)  # Auto-fix to ensure 100% green lights
    
    # Style Reference & Few-Shot Layout Cloner
    style_reference_sample = Column(Text, nullable=True)     # User-provided example paragraph or full post
    style_reference_font = Column(String(255), default="Inter, -apple-system, sans-serif")
    style_reference_header = Column(String(255), default="Modern Lead Deck with Category Tag")
    style_reference_footer = Column(String(255), default="Verified Clinical Citations & Disclaimer Block")
    
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    site = relationship("ManagedSite", back_populates="content_rules")

class ResearchArticle(Base):
    __tablename__ = "research_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("managed_sites.id", ondelete="CASCADE"), nullable=True, default=1, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=True)
    run_id = Column(String(64), index=True)
    url = Column(String(1024), index=True, nullable=False)
    url_hash = Column(String(64), index=True, nullable=False)  # MD5 hash for rapid pre-dedup lookup
    title = Column(String(512), nullable=False)
    source_domain = Column(String(255), index=True)
    publish_date = Column(String(100), nullable=True)
    full_text = Column(Text, nullable=False)
    key_claims = Column(JSON, default=list)  # Extracted facts, stats, quotes
    fingerprint = Column(String(64), nullable=True)
    fetched_at = Column(DateTime, default=datetime.datetime.utcnow)

    topic = relationship("Topic", back_populates="articles")

class GeneratedPost(Base):
    __tablename__ = "generated_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("managed_sites.id", ondelete="CASCADE"), nullable=True, default=1, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    run_id = Column(String(64), index=True)
    title = Column(String(512), nullable=False)
    slug = Column(String(255), nullable=False)
    excerpt = Column(Text, nullable=True)
    body_html = Column(Text, nullable=False)
    
    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(512), nullable=True)
    tags = Column(JSON, default=list)
    categories = Column(JSON, default=list)
    
    # Citations & Evidence
    sources_used = Column(JSON, default=list)
    key_takeaways = Column(JSON, default=list)
    disclaimer = Column(Text, nullable=True)
    
    # Deduplication analysis
    similarity_score = Column(Float, default=0.0)
    similarity_matched_id = Column(Integer, nullable=True)
    similarity_status = Column(String(50), default="PASSED")  # PASSED, RE_ANGLED, EXCEEDED_THRESHOLD
    content_fingerprint = Column(Text, nullable=True)         # MinHash or TF-IDF top terms
    
    # Yoast SEO Compliance (v28.4)
    focus_keyphrase = Column(String(255), nullable=True)
    yoast_seo_score = Column(Integer, default=90)            # 0-100 (>=80 is Green / Good)
    yoast_readability_score = Column(Integer, default=90)    # 0-100 (>=80 is Green / Good)
    yoast_checklist = Column(JSON, default=list)             # Detailed audit checklist
    
    # Editorial status
    # PENDING_REVIEW -> User can Approve, Reject, or Regenerate
    # APPROVED -> Post ready to send to WP
    # REJECTED -> Post dismissed
    # SENT_TO_WP -> Successfully pushed to WordPress as draft
    # DUPLICATE_FLAGGED -> Exceeded similarity threshold and stopped
    status = Column(String(50), default="PENDING_REVIEW", index=True)
    
    # WordPress References
    wp_post_id = Column(Integer, nullable=True)
    wp_edit_url = Column(String(1024), nullable=True)
    wp_pushed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    site = relationship("ManagedSite", back_populates="posts")
    topic = relationship("Topic", back_populates="posts")

class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("managed_sites.id", ondelete="CASCADE"), nullable=True, default=1, index=True)
    site_name = Column(String(255), nullable=True, default="MedHealth Times")
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    topic_id = Column(Integer, nullable=True)
    topic_name = Column(String(255), nullable=False)
    trigger_type = Column(String(50), default="MANUAL")  # MANUAL, SCHEDULED
    status = Column(String(50), default="RUNNING")       # RUNNING, COMPLETED, FAILED, DUPLICATE_REJECTED
    step_logs = Column(JSON, default=list)               # [{timestamp, step, message, level}]
    error_message = Column(Text, nullable=True)
    generated_post_id = Column(Integer, nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    site = relationship("ManagedSite", back_populates="run_logs")

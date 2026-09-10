from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- Topic Schemas ---
class TopicBase(BaseModel):
    name: str = Field(..., description="Unique name of the topic category")
    keywords: List[str] = Field(default_factory=list, description="Search queries / keywords")
    weight: int = Field(5, ge=1, le=10, description="Priority weight 1-10")
    is_active: bool = Field(True, description="Whether this topic is included in runs")
    domain_whitelist: List[str] = Field(default_factory=list, description="Trusted domains whitelist")
    domain_blocklist: List[str] = Field(default_factory=list, description="Blocked domains")
    lookback_days: int = Field(7, ge=1, le=90, description="Lookback window in days")

class TopicCreate(TopicBase):
    pass

class TopicUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    weight: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None
    domain_whitelist: Optional[List[str]] = None
    domain_blocklist: Optional[List[str]] = None
    lookback_days: Optional[int] = Field(None, ge=1, le=90)

class TopicResponse(TopicBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TopicBulkImport(BaseModel):
    raw_text: str = Field(..., description="Bulk raw text of topics/keywords to parse")

# --- Content Rules Schemas ---
class ContentRuleBase(BaseModel):
    name: str = "Default Publishing Rules"
    is_active: bool = True
    tone: str = "Professional & Informative"
    reading_level: str = "General Public (Clear, Accessible)"
    word_count_min: int = Field(800, ge=300)
    word_count_max: int = Field(1200, le=5000)
    heading_structure: str = "H1 Title, 3-4 H2 Sections, H3 Sub-points"
    include_takeaways: bool = True
    include_faq: bool = True
    include_disclaimer: bool = True
    include_quotes: bool = True
    include_sources: bool = True
    disclaimer_text: str = "Disclaimer: This article is for informational purposes only and does not constitute medical advice or formal clinical diagnosis. Consult a qualified healthcare professional before making health-related decisions."
    style_guide_text: str = "Maintain scientific accuracy. Avoid sensational headlines like 'miracle cure' or 'breakthrough.' Always clearly state clinical trial phases and acknowledge sample sizes or study limitations."
    seo_rules: Dict[str, Any] = Field(default_factory=lambda: {
        "meta_description_max_length": 155,
        "target_keyword_density": "1-2%",
        "slug_format": "kebab-case-keyword-rich",
        "generate_image_alt": True
    })
    auto_push_to_wp: bool = False
    enforce_yoast_green: bool = True
    style_reference_sample: Optional[str] = None
    style_reference_font: Optional[str] = "Inter, -apple-system, sans-serif"
    style_reference_header: Optional[str] = "Modern Lead Deck with Category Tag"
    style_reference_footer: Optional[str] = "Verified Clinical Citations & Disclaimer Block"

class ContentRuleUpdate(BaseModel):
    tone: Optional[str] = None
    reading_level: Optional[str] = None
    word_count_min: Optional[int] = None
    word_count_max: Optional[int] = None
    heading_structure: Optional[str] = None
    include_takeaways: Optional[bool] = None
    include_faq: Optional[bool] = None
    include_disclaimer: Optional[bool] = None
    include_quotes: Optional[bool] = None
    include_sources: Optional[bool] = None
    disclaimer_text: Optional[str] = None
    style_guide_text: Optional[str] = None
    seo_rules: Optional[Dict[str, Any]] = None
    auto_push_to_wp: Optional[bool] = None
    enforce_yoast_green: Optional[bool] = None
    style_reference_sample: Optional[str] = None
    style_reference_font: Optional[str] = None
    style_reference_header: Optional[str] = None
    style_reference_footer: Optional[str] = None

class ContentRuleResponse(ContentRuleBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Research Article Schemas ---
class ResearchArticleResponse(BaseModel):
    id: int
    topic_id: Optional[int]
    run_id: str
    url: str
    title: str
    source_domain: Optional[str]
    publish_date: Optional[str]
    key_claims: List[Any]
    fetched_at: datetime

    class Config:
        from_attributes = True

# --- Generated Post Schemas ---
class GeneratedPostResponse(BaseModel):
    id: int
    topic_id: Optional[int]
    run_id: str
    title: str
    slug: str
    excerpt: Optional[str]
    body_html: str
    meta_title: Optional[str]
    meta_description: Optional[str]
    tags: List[str]
    categories: List[str]
    sources_used: List[Any]
    key_takeaways: List[str]
    disclaimer: Optional[str]
    similarity_score: float
    similarity_matched_id: Optional[int]
    similarity_status: str
    
    # Yoast SEO Compliance fields
    focus_keyphrase: Optional[str] = None
    yoast_seo_score: int = 90
    yoast_readability_score: int = 90
    yoast_checklist: List[Dict[str, Any]] = Field(default_factory=list)
    
    status: str
    wp_post_id: Optional[int]
    wp_edit_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class DraftReviewAction(BaseModel):
    action: str = Field(..., description="'approve', 'reject', 'regenerate', or 'push_to_wp'")
    feedback: Optional[str] = Field(None, description="Optional instruction/angle redirection if regenerating")

# --- Run & Scheduler Schemas ---
class RunTriggerRequest(BaseModel):
    topic_id: Optional[int] = Field(None, description="Specific topic to run, or null to run all active")
    force_fresh_search: bool = True

class RunLogResponse(BaseModel):
    id: int
    run_id: str
    topic_id: Optional[int]
    topic_name: str
    trigger_type: str
    status: str
    step_logs: List[Dict[str, Any]]
    error_message: Optional[str]
    generated_post_id: Optional[int]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- Auth Schemas ---
class AuthLoginRequest(BaseModel):
    password: str

class AuthLoginResponse(BaseModel):
    success: bool
    token: str
    developer_name: str
    message: str

# --- Settings & Health Schemas ---
class SettingsResponse(BaseModel):
    ai_provider: str = "openrouter"
    openrouter_api_key_configured: bool = False
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    anthropic_api_key_configured: bool
    anthropic_model: str
    search_provider: str
    serpapi_key_configured: bool
    newsapi_key_configured: bool
    bing_key_configured: bool
    wordpress_url: str
    wordpress_api_key_configured: bool
    dedup_threshold: float
    auto_push_to_wp: bool
    scheduler_enabled: bool
    scheduler_interval_hours: int
    developer_name: str = "Krish Goswami"

class SettingsUpdate(BaseModel):
    ai_provider: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    anthropic_model: Optional[str] = None
    search_provider: Optional[str] = None
    serpapi_api_key: Optional[str] = None
    newsapi_api_key: Optional[str] = None
    bing_api_key: Optional[str] = None
    wordpress_url: Optional[str] = None
    wordpress_api_key: Optional[str] = None
    dedup_threshold: Optional[float] = None
    auto_push_to_wp: Optional[bool] = None
    scheduler_enabled: Optional[bool] = None
    scheduler_interval_hours: Optional[int] = None
    developer_password: Optional[str] = None

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- Managed Site Schemas ---
class SiteBase(BaseModel):
    name: str = Field(..., description="Display name of the website")
    slug: Optional[str] = Field(None, description="Unique slug identifier (generated if omitted)")
    wp_url: str = Field(..., description="WordPress site base URL")
    wp_api_key: str = Field(..., description="WordPress stealth API key (X-Pulse-Sync-Key)")
    description: Optional[str] = Field(None, description="Niche or content focus description")
    is_active: bool = Field(True, description="Whether this site is active")
    auto_push_to_wp: bool = Field(False, description="Whether to automatically push approved drafts to WordPress")
    is_scheduler_enabled: bool = Field(False, description="Whether the background cron scheduler runs for this site")
    schedule_interval_hours: int = Field(6, ge=1, le=168, description="Cron interval in hours")

class SiteCreate(SiteBase):
    pass

class SiteUpdate(BaseModel):
    name: Optional[str] = None
    wp_url: Optional[str] = None
    wp_api_key: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    auto_push_to_wp: Optional[bool] = None
    is_scheduler_enabled: Optional[bool] = None
    schedule_interval_hours: Optional[int] = Field(None, ge=1, le=168)

class SiteResponse(BaseModel):
    id: int
    name: str
    slug: str
    wp_url: str
    wp_api_key_masked: str
    description: Optional[str] = None
    is_active: bool
    auto_push_to_wp: bool
    is_scheduler_enabled: bool
    schedule_interval_hours: int
    topics_count: int = 0
    drafts_count: int = 0
    published_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SiteTestResponse(BaseModel):
    connected: bool
    status_code: int
    message: str
    site_name: Optional[str] = None
    plugin_version: Optional[str] = None

# --- Topic Schemas ---
class TopicBase(BaseModel):
    site_id: Optional[int] = Field(1, description="Associated Managed Site ID")
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
    site_id: Optional[int] = None
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    weight: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None
    domain_whitelist: Optional[List[str]] = None
    domain_blocklist: Optional[List[str]] = None
    lookback_days: Optional[int] = Field(None, ge=1, le=90)

class TopicResponse(TopicBase):
    id: int
    site_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TopicBulkImport(BaseModel):
    site_id: Optional[int] = Field(1, description="Associated Managed Site ID")
    raw_text: str = Field(..., description="Bulk raw text of topics/keywords to parse")

# --- Content Rules Schemas ---
class ContentRuleBase(BaseModel):
    site_id: Optional[int] = Field(1, description="Associated Managed Site ID")
    name: str = "Default Publishing Rules"
    is_active: bool = True
    tone: str = "Professional & Informative"
    reading_level: str = "General Public (Clear, Accessible)"
    word_count_min: int = Field(450, ge=300)
    word_count_max: int = Field(520, le=5000)
    heading_structure: str = "<h6><strong>Heading Title</strong></h6>"
    include_takeaways: bool = False
    include_faq: bool = False
    include_disclaimer: bool = False
    include_quotes: bool = False
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
    site_id: Optional[int] = 1
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
    site_id: Optional[int] = 1
    site_name: Optional[str] = None
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
    
    # Token Economics & Cost Analytics
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    cost_breakdown: Dict[str, Any] = Field(default_factory=dict)

    status: str
    wp_post_id: Optional[int]
    wp_edit_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class DraftReviewAction(BaseModel):
    action: str = Field(..., description="'approve', 'reject', 'delete', 'regenerate', or 'push_to_wp'")
    feedback: Optional[str] = Field(None, description="Optional instruction/angle redirection if regenerating")

class DraftBulkDeleteRequest(BaseModel):
    post_ids: Optional[List[int]] = Field(default_factory=list, description="List of post IDs to delete")
    delete_all: Optional[bool] = Field(False, description="If true, deletes all posts matching optional status")
    status: Optional[str] = Field(None, description="Optional status filter for delete_all (e.g. DUPLICATE_FLAGGED)")

class DraftBulkDeleteResponse(BaseModel):
    success: bool
    deleted_count: int
    message: str

class DraftBulkPushRequest(BaseModel):
    post_ids: Optional[List[int]] = Field(default_factory=list, description="List of post IDs to push to WordPress")
    site_id: Optional[int] = Field(None, description="Target site ID if pushing all pending")
    all_pending: bool = Field(False, description="If true, pushes all pending/approved drafts for site")

# --- Run & Scheduler Schemas ---
class RunTriggerRequest(BaseModel):
    site_id: Optional[int] = Field(None, description="Target site ID (null executes for active topic/site)")
    topic_id: Optional[int] = Field(None, description="Specific topic to run, or null to run all active")
    force_fresh_search: bool = True

class RunLogResponse(BaseModel):
    id: int
    site_id: Optional[int] = 1
    site_name: Optional[str] = "MedHealth Times"
    run_id: str
    topic_id: Optional[int]
    topic_name: str
    trigger_type: str
    status: str
    step_logs: List[Dict[str, Any]]
    error_message: Optional[str]
    generated_post_id: Optional[int]
    
    # Token Economics & Cost Analytics
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    cost_breakdown: Dict[str, Any] = Field(default_factory=dict)

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
    
    # Token Economics & Cost Analytics
    cost_currency: str = "USD"
    cost_exchange_rate: float = 87.5
    cost_prompt_per_1m: float = 0.15
    cost_completion_per_1m: float = 0.60
    cost_per_search_query: float = 0.0015
    cost_manual_override_enabled: bool = False
    cost_fixed_per_post: float = 0.0035

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
    
    # Token Economics & Cost Analytics
    cost_currency: Optional[str] = None
    cost_exchange_rate: Optional[float] = None
    cost_prompt_per_1m: Optional[float] = None
    cost_completion_per_1m: Optional[float] = None
    cost_per_search_query: Optional[float] = None
    cost_manual_override_enabled: Optional[bool] = None
    cost_fixed_per_post: Optional[float] = None

# --- Cost & Token Analytics Schemas ---
class CostStageDetail(BaseModel):
    id: str
    name: str
    percentage: int
    tokens: int
    cost_usd: float
    cost_converted: float
    formatted_cost: str
    description: str
    metrics: List[str]

class CostBreakdownResponse(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    total_cost_converted: float
    formatted_total_cost: str
    currency: str
    currency_symbol: str
    exchange_rate: float
    is_manual_override: bool
    stages: List[CostStageDetail]
    rates: Dict[str, Any]

class CostAnalyticsSummaryResponse(BaseModel):
    currency: str
    currency_symbol: str
    total_topics_count: int
    active_topics_count: int
    scheduler_interval_hours: int
    single_post: Dict[str, Any]
    full_catalog_run: Dict[str, Any]
    projections: Dict[str, Any]
    sample_post_breakdown: CostBreakdownResponse

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- Competitor Price Schemas ---
class CompetitorPriceBase(BaseModel):
    competitor_name: str
    raw_price: Optional[float] = None
    discount: float = 0.0
    net_price: Optional[float] = None
    stock_status: str = "IN_STOCK"
    is_suspicious: bool = False
    voucher_details: Optional[str] = None
    promo_mechanics: Optional[str] = None
    url: Optional[str] = None

class CompetitorPriceCreate(CompetitorPriceBase):
    product_id: int

class CompetitorPrice(CompetitorPriceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    scraped_at: datetime

# --- Pricing Index Schemas ---
class PricingIndexBase(BaseModel):
    competitor_index: float
    average_competitor_price: float
    recommendation: str

class PricingIndex(PricingIndexBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    updated_at: datetime

# --- Alert Schemas ---
class AlertBase(BaseModel):
    alert_type: str
    message: str
    severity: str
    is_resolved: bool


class AlertProductRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class Alert(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    created_at: datetime
    product: Optional[AlertProductRef] = None

# --- Product Schemas ---
class ProductBase(BaseModel):
    barcode: str
    name: str
    category: str
    guardian_price: float
    cost_price: float = 0.0
    image_url: Optional[str] = None
    description: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    guardian_price: Optional[float] = None
    cost_price: Optional[float] = None
    image_url: Optional[str] = None
    description: Optional[str] = None

class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    
    # We can nest related items if needed, or query them separately.
    pricing_indices: List[PricingIndex] = []
    alerts: List[Alert] = []

# --- Combined Product Details ---
class ProductDetail(Product):
    competitor_prices: List[CompetitorPrice] = []

# --- Overview Statistics Schemas ---
class OverviewStats(BaseModel):
    average_cpi: float
    total_sku: int
    underpriced_sku: int # Guardian is cheaper than competitors (CPI < 90)
    overpriced_sku: int  # Guardian is more expensive (CPI > 110)
    high_severity_alerts: int
    category_distribution: dict
    competitor_avg_prices: dict


class ChannelPricingIndex(BaseModel):
    channel: str
    cpi: float
    price_gap_pct: float
    position: str
    avg_guardian_price: float
    avg_net_price: float
    sku_coverage: int
    coverage_pct: float
    observation_coverage_pct: float
    freshness_pct: float
    data_quality_pct: float
    promotion_sku: int
    promotion_coverage_pct: float
    voucher_sku: int
    bundle_sku: int
    flash_sale_sku: int
    guardian_premium_sku: int
    guardian_value_sku: int
    opportunity_count: int
    latest_scrape_at: Optional[datetime] = None


class ChannelIntelligenceSummary(BaseModel):
    target_sku: int
    monitored_sku: int
    target_coverage_pct: float
    observed_sku: int
    fresh_sku: int
    configured_channels: int
    channels_with_data: int
    overall_cpi: float
    automated_observation_coverage_pct: float
    valid_observation_pct: float
    fresh_observation_pct: float
    freshness_sla_hours: int
    promotion_observations: int
    pricing_opportunities: int
    latest_observation_at: Optional[datetime] = None
    latest_observation_age_hours: Optional[float] = None


class ChannelIntelligence(BaseModel):
    summary: ChannelIntelligenceSummary
    channels: List[ChannelPricingIndex]

# --- Agentic AI Schemas ---
class AgentActionBase(BaseModel):
    action_type: str
    description: str
    status: str = "Pending"
    data: Optional[str] = None

class AgentAction(AgentActionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    product_id: int
    created_at: datetime

class AgentTaskBase(BaseModel):
    objective: str
    status: str
    logs: Optional[str] = None

class AgentTask(AgentTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    actions: List[AgentAction] = []

class AgentConfig(BaseModel):
    underprice_threshold: float
    overprice_threshold: float
    min_margin: float
    custom_instruction: str


class AgentBriefingSummary(BaseModel):
    monitored_sku: int
    active_alerts: int
    high_severity_alerts: int
    pending_actions: int
    average_cpi: float
    channels_covered: int
    last_scrape_at: Optional[datetime] = None


class AgentBriefingChannel(BaseModel):
    channel: str
    avg_net_price: float
    sku_coverage: int
    alert_count: int
    cpi: float = 100.0
    coverage_pct: float = 0.0
    freshness_pct: float = 0.0
    promotion_sku: int = 0
    opportunity_count: int = 0


class AgentBriefingPriority(BaseModel):
    alert_id: int
    product_id: int
    product_name: str
    category: str
    guardian_price: float
    cost_price: float
    current_margin_pct: float
    competitor_name: str
    competitor_price: float
    price_gap_pct: float
    margin_if_matched_pct: float
    strategy: str
    recommended_action: str
    rationale: str
    severity: str
    message: str
    channel_url: Optional[str] = None
    scraped_at: Optional[datetime] = None


class AgentBriefing(BaseModel):
    summary: AgentBriefingSummary
    priority_queue: List[AgentBriefingPriority]
    channel_summary: List[AgentBriefingChannel]
    latest_task: Optional[AgentTask] = None


class ScrapeSampleMatch(BaseModel):
    product_id: int
    product_name: str
    guardian_price: float
    category: str


class ScrapeSample(BaseModel):
    source: str
    platform: str
    kind: str
    title: str
    brand: Optional[str] = None
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    discount_pct: Optional[float] = None
    rating: Optional[float] = None
    url: Optional[str] = None
    record_count: int
    match: Optional[ScrapeSampleMatch] = None

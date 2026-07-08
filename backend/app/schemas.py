from pydantic import BaseModel, Field
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
    id: int
    product_id: int
    scraped_at: datetime

    class Config:
        from_attributes = True

# --- Pricing Index Schemas ---
class PricingIndexBase(BaseModel):
    competitor_index: float
    average_competitor_price: float
    recommendation: str

class PricingIndex(PricingIndexBase):
    id: int
    product_id: int
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Alert Schemas ---
class AlertBase(BaseModel):
    alert_type: str
    message: str
    severity: str
    is_resolved: bool


class AlertProductRef(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class Alert(AlertBase):
    id: int
    product_id: int
    created_at: datetime
    product: Optional[AlertProductRef] = None

    class Config:
        from_attributes = True

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
    id: int
    created_at: datetime
    updated_at: datetime
    
    # We can nest related items if needed, or query them separately.
    pricing_indices: List[PricingIndex] = []
    alerts: List[Alert] = []

    class Config:
        from_attributes = True

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

# --- Agentic AI Schemas ---
class AgentActionBase(BaseModel):
    action_type: str
    description: str
    status: str = "Pending"
    data: Optional[str] = None

class AgentAction(AgentActionBase):
    id: int
    task_id: int
    product_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AgentTaskBase(BaseModel):
    objective: str
    status: str
    logs: Optional[str] = None

class AgentTask(AgentTaskBase):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    actions: List[AgentAction] = []

    class Config:
        from_attributes = True

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

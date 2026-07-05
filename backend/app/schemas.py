from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Competitor Price Schemas ---
class CompetitorPriceBase(BaseModel):
    competitor_name: str
    raw_price: float
    discount: float
    net_price: float
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

class Alert(AlertBase):
    id: int
    product_id: int
    created_at: datetime

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


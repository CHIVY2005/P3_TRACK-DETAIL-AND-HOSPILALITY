from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    guardian_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False, default=0.0) # Cost price to calculate profit margins
    image_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    competitor_prices = relationship("CompetitorPrice", back_populates="product", cascade="all, delete-orphan")
    pricing_indices = relationship("PricingIndex", back_populates="product", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="product", cascade="all, delete-orphan")


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    competitor_name = Column(String(100), index=True, nullable=False)  # Shopee, Lazada, TikTok Shop, etc.
    raw_price = Column(Float, nullable=True)
    discount = Column(Float, default=0.0)
    net_price = Column(Float, nullable=True)
    stock_status = Column(String(50), default="IN_STOCK", nullable=False) # IN_STOCK, OUT_OF_STOCK
    voucher_details = Column(String(255), nullable=True)
    promo_mechanics = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="competitor_prices")


class PricingIndex(Base):
    __tablename__ = "pricing_indices"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    competitor_index = Column(Float, nullable=False)  # CPI: (Guardian / Avg Competitor) * 100
    average_competitor_price = Column(Float, nullable=False)
    recommendation = Column(String(100), nullable=False)  # Maintain, Lower Price, Increase Price
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="pricing_indices")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # Underpriced, Overpriced, Promo Active
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # Low, Medium, High
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="alerts")


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    objective = Column(String(255), nullable=False)
    status = Column(String(50), default="Pending", nullable=False) # Pending, Running, Completed, Failed
    logs = Column(Text, nullable=True) # Thoughts and observations
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    actions = relationship("AgentAction", back_populates="task", cascade="all, delete-orphan")


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(100), nullable=False) # AUTO_PRICE_MATCH, SUPPLIER_EMAIL_DRAFT, etc.
    description = Column(Text, nullable=False)
    status = Column(String(50), default="Pending", nullable=False) # Pending, Approved, Rejected, Executed
    data = Column(Text, nullable=True) # Extra data like email text or raw values
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("AgentTask", back_populates="actions")
    product = relationship("Product")

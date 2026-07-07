from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base

class SkuMaster(Base):
    """
    Guardian's internal sku master data.
    """
    __tablename__ = "sku_master"

    barcode = Column(String, primary_key=True, index=True)
    product_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    guardian_price = Column(Integer, nullable=False)
    
    # Vector embedding for AI-driven product name matching (dimension=384)
    name_embedding = Column(Vector(384))
    
    # Relationships
    competitor_links = relationship("CompetitorLink", back_populates="sku")
    price_history = relationship("PriceHistory", back_populates="sku")


class CompetitorLink(Base):
    """
    Mapping URLs to crawl for competitors.
    """
    __tablename__ = "competitor_links"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, ForeignKey("sku_master.barcode"), nullable=False)
    platform = Column(String, nullable=False) # e.g., 'Hasaki', 'Shopee'
    url = Column(String, nullable=False)
    platform_item_id = Column(String, nullable=True)
    
    # Relationships
    sku = relationship("SkuMaster", back_populates="competitor_links")


class PriceHistory(Base):
    """
    The scraped pricing results from competitors.
    """
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, ForeignKey("sku_master.barcode"), nullable=False)
    platform = Column(String, nullable=False)
    scraped_price = Column(Integer, nullable=False)
    promotion = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sku = relationship("SkuMaster", back_populates="price_history")

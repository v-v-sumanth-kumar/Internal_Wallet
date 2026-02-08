"""Asset Type Model - Represents different types of virtual currencies"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class AssetType(Base):
    """Asset Type Model
    
    Represents different types of virtual currencies in the system
    Examples: Gold Coins, Diamonds, Loyalty Points
    """
    __tablename__ = "asset_types"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AssetType(id={self.id}, code='{self.code}', name='{self.name}')>"

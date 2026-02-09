from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Wallet(Base):
    """Wallet Model
    
    Represents a wallet that holds a specific asset type for a user or system account
    Each user can have multiple wallets (one per asset type)
    """
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)  
    asset_type_id = Column(Integer, ForeignKey("asset_types.id"), nullable=False)
    balance = Column(Numeric(precision=20, scale=2), default=0, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  
    version = Column(Integer, default=0, nullable=False)  
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'asset_type_id', name='uq_user_asset'),
        Index('idx_wallet_user_asset', 'user_id', 'asset_type_id'),
    )
    
    def __repr__(self):
        return f"<Wallet(id={self.id}, user_id='{self.user_id}', balance={self.balance})>"

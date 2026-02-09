from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum, Index
from sqlalchemy.sql import func
import enum
from app.database import Base


class TransactionType(str, enum.Enum):
    """Transaction Types"""
    TOPUP = "TOPUP"          
    BONUS = "BONUS"          
    SPEND = "SPEND"          
    REFUND = "REFUND"        
    ADJUSTMENT = "ADJUSTMENT" 


class TransactionStatus(str, enum.Enum):
    """Transaction Status"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class Transaction(Base):
    """Transaction Model
    
    Represents a transaction between two wallets
    Every transaction creates corresponding ledger entries
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)  
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True)
    
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    
    from_wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    to_wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    asset_type_id = Column(Integer, ForeignKey("asset_types.id"), nullable=False)
    
    amount = Column(Numeric(precision=20, scale=2), nullable=False)
    description = Column(String(500))
    meta_data = Column(String(1000))  
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_transaction_type_status', 'transaction_type', 'status'),
        Index('idx_transaction_wallets', 'from_wallet_id', 'to_wallet_id'),
        Index('idx_transaction_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.transaction_type}, amount={self.amount}, status={self.status})>"

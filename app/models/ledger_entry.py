from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Enum, Index
from sqlalchemy.sql import func
import enum
from app.database import Base


class EntryType(str, enum.Enum):
    """Ledger Entry Types"""
    DEBIT = "DEBIT"   
    CREDIT = "CREDIT"  


class LedgerEntry(Base):
    """Ledger Entry Model
    
    Implements double-entry bookkeeping
    Every transaction creates two entries: one debit and one credit
    Balance = SUM of all ledger entries for a wallet
    """
    __tablename__ = "ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    
    entry_type = Column(Enum(EntryType), nullable=False)
    amount = Column(Numeric(precision=20, scale=2), nullable=False) 
    
    balance_after = Column(Numeric(precision=20, scale=2), nullable=False)  
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_ledger_wallet_created', 'wallet_id', 'created_at'),
        Index('idx_ledger_transaction', 'transaction_id'),
    )
    
    def __repr__(self):
        return f"<LedgerEntry(id={self.id}, wallet_id={self.wallet_id}, type={self.entry_type}, amount={self.amount})>"

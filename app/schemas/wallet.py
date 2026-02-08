"""Wallet Schemas - Request/Response Models"""
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime
from typing import Optional, List


class TopupRequest(BaseModel):
    """Request schema for wallet top-up (purchase)"""
    user_id: str = Field(..., description="User identifier")
    asset_type_code: str = Field(..., description="Asset type code (e.g., GOLD_COIN)")
    amount: Decimal = Field(..., gt=0, description="Amount to top-up (must be positive)")
    payment_reference: Optional[str] = Field(None, description="Payment gateway reference")
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        # Ensure max 2 decimal places
        if v.as_tuple().exponent < -2:
            raise ValueError('Amount cannot have more than 2 decimal places')
        return v


class BonusRequest(BaseModel):
    """Request schema for bonus/incentive credits"""
    user_id: str = Field(..., description="User identifier")
    asset_type_code: str = Field(..., description="Asset type code")
    amount: Decimal = Field(..., gt=0, description="Bonus amount (must be positive)")
    reason: str = Field(..., max_length=500, description="Reason for bonus (e.g., referral, promo)")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        if v.as_tuple().exponent < -2:
            raise ValueError('Amount cannot have more than 2 decimal places')
        return v


class SpendRequest(BaseModel):
    """Request schema for spending credits"""
    user_id: str = Field(..., description="User identifier")
    asset_type_code: str = Field(..., description="Asset type code")
    amount: Decimal = Field(..., gt=0, description="Amount to spend (must be positive)")
    item_id: Optional[str] = Field(None, description="ID of item being purchased")
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        if v.as_tuple().exponent < -2:
            raise ValueError('Amount cannot have more than 2 decimal places')
        return v


class TransactionResponse(BaseModel):
    """Response schema for transaction operations"""
    transaction_id: str
    transaction_type: str
    status: str
    from_wallet_id: int
    to_wallet_id: int
    amount: Decimal
    description: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class WalletBalanceResponse(BaseModel):
    """Response schema for wallet balance"""
    wallet_id: int
    user_id: str
    asset_type_code: str
    balance: Decimal
    is_system: bool
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LedgerEntryResponse(BaseModel):
    """Response schema for ledger entry"""
    id: int
    entry_type: str
    amount: Decimal
    balance_after: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransactionHistoryResponse(BaseModel):
    """Response schema for transaction history"""
    transactions: List[TransactionResponse]
    total_count: int
    page: int
    page_size: int


class WalletResponse(BaseModel):
    """Detailed wallet response with transaction history"""
    wallet_id: int
    user_id: str
    asset_type_code: str
    balance: Decimal
    recent_transactions: List[TransactionResponse]
    
    class Config:
        from_attributes = True

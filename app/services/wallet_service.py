from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import json
from typing import Optional, List, Tuple

from app.models import (
    Wallet,
    Transaction,
    LedgerEntry,
    AssetType,
    IdempotencyLog,
)
from app.models.transaction import TransactionType, TransactionStatus
from app.models.ledger_entry import EntryType
from app.config import settings


class InsufficientFundsError(Exception):
    """Raised when wallet has insufficient balance"""
    pass


class AssetTypeNotFoundError(Exception):
    """Raised when asset type is not found"""
    pass


class WalletNotFoundError(Exception):
    """Raised when wallet is not found"""
    pass


class DuplicateTransactionError(Exception):
    """Raised when duplicate transaction is detected"""
    pass


class WalletService:
    """Wallet Service - Handles all wallet operations with ACID guarantees"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def _check_idempotency(self, idempotency_key: str, request_path: str, request_method: str) -> Optional[dict]:
        """
        Check if request with this idempotency key was already processed
        Returns cached response if found, None otherwise
        """
        stmt = select(IdempotencyLog).where(
            and_(
                IdempotencyLog.idempotency_key == idempotency_key,
                IdempotencyLog.expires_at > datetime.utcnow()
            )
        )
        result = await self.db.execute(stmt)
        log = result.scalar_one_or_none()
        
        if log:
            # Return cached response
            return {
                "status": log.response_status,
                "body": json.loads(log.response_body) if log.response_body else None
            }
        
        return None
    
    async def _save_idempotency_log(
        self,
        idempotency_key: str,
        request_path: str,
        request_method: str,
        response_status: int,
        response_body: dict
    ):
        """Save idempotency log for future duplicate checks"""
        expires_at = datetime.utcnow() + timedelta(hours=24)  # Keep for 24 hours
        
        log = IdempotencyLog(
            idempotency_key=idempotency_key,
            request_path=request_path,
            request_method=request_method,
            response_status=response_status,
            response_body=json.dumps(response_body),
            expires_at=expires_at
        )
        
        self.db.add(log)
        await self.db.flush()
    
    async def _get_or_create_wallet(self, user_id: str, asset_type_id: int, is_system: bool = False) -> Wallet:
        """
        Get existing wallet or create new one
        Uses SELECT FOR UPDATE to prevent race conditions
        """
        stmt = select(Wallet).where(
            and_(
                Wallet.user_id == user_id,
                Wallet.asset_type_id == asset_type_id
            )
        ).with_for_update()
        
        result = await self.db.execute(stmt)
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            wallet = Wallet(
                user_id=user_id,
                asset_type_id=asset_type_id,
                balance=Decimal('0.00'),
                is_system=is_system,
                version=0
            )
            self.db.add(wallet)
            await self.db.flush()
        
        return wallet
    
    async def _get_asset_type_by_code(self, code: str) -> AssetType:
        """Get asset type by code"""
        stmt = select(AssetType).where(
            and_(
                AssetType.code == code,
                AssetType.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        asset_type = result.scalar_one_or_none()
        
        if not asset_type:
            raise AssetTypeNotFoundError(f"Asset type '{code}' not found or inactive")
        
        return asset_type
    
    async def _execute_transaction(
        self,
        from_wallet_id: int,
        to_wallet_id: int,
        asset_type_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        idempotency_key: str,
        description: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Transaction:
        """
        Execute a transaction with double-entry ledger
        Uses pessimistic locking (SELECT FOR UPDATE) to prevent race conditions
        
        DEADLOCK AVOIDANCE: Always lock wallets in ascending ID order
        """
        # CRITICAL: Lock wallets in consistent order to avoid deadlocks
        wallet_ids = sorted([from_wallet_id, to_wallet_id])
        
        # Lock both wallets in ascending order
        stmt = select(Wallet).where(
            Wallet.id.in_(wallet_ids)
        ).with_for_update().order_by(Wallet.id)
        
        result = await self.db.execute(stmt)
        wallets = {w.id: w for w in result.scalars().all()}
        
        from_wallet = wallets.get(from_wallet_id)
        to_wallet = wallets.get(to_wallet_id)
        
        if not from_wallet or not to_wallet:
            raise WalletNotFoundError("One or both wallets not found")
        
        # Check sufficient balance (only for non-system wallets)
        if not from_wallet.is_system and from_wallet.balance < amount:
            raise InsufficientFundsError(
                f"Insufficient balance. Available: {from_wallet.balance}, Required: {amount}"
            )
        
        # Create transaction record
        transaction_id = str(uuid.uuid4())
        transaction = Transaction(
            transaction_id=transaction_id,
            idempotency_key=idempotency_key,
            transaction_type=transaction_type,
            status=TransactionStatus.PENDING,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            asset_type_id=asset_type_id,
            amount=amount,
            description=description,
            meta_data=json.dumps(metadata) if metadata else None,
        )
        self.db.add(transaction)
        await self.db.flush()
        
        # Update balances
        from_wallet.balance -= amount
        to_wallet.balance += amount
        
        # Create double-entry ledger entries
        debit_entry = LedgerEntry(
            transaction_id=transaction.id,
            wallet_id=from_wallet_id,
            entry_type=EntryType.DEBIT,
            amount=-amount,
            balance_after=from_wallet.balance
        )
        
        credit_entry = LedgerEntry(
            transaction_id=transaction.id,
            wallet_id=to_wallet_id,
            entry_type=EntryType.CREDIT,
            amount=amount,
            balance_after=to_wallet.balance
        )
        
        self.db.add_all([debit_entry, credit_entry])
        
        # Mark transaction as completed
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.utcnow()
        
        await self.db.flush()
        
        return transaction
    
    async def topup_wallet(
        self,
        user_id: str,
        asset_type_code: str,
        amount: Decimal,
        idempotency_key: str,
        payment_reference: Optional[str] = None,
        description: Optional[str] = None
    ) -> Transaction:
        """
        Top-up user wallet (Purchase flow)
        Money flows from System Treasury to User Wallet
        """
        # Get asset type
        asset_type = await self._get_asset_type_by_code(asset_type_code)
        
        # Get or create user wallet
        user_wallet = await self._get_or_create_wallet(user_id, asset_type.id, is_system=False)
        
        # Get system treasury wallet
        treasury_wallet = await self._get_or_create_wallet(
            f"SYSTEM_TREASURY_{asset_type_code}",
            asset_type.id,
            is_system=True
        )
        
        # Execute transaction
        metadata = {
            "payment_reference": payment_reference,
            "flow": "topup"
        }
        
        transaction = await self._execute_transaction(
            from_wallet_id=treasury_wallet.id,
            to_wallet_id=user_wallet.id,
            asset_type_id=asset_type.id,
            amount=amount,
            transaction_type=TransactionType.TOPUP,
            idempotency_key=idempotency_key,
            description=description or f"Wallet top-up for {user_id}",
            metadata=metadata
        )
        
        return transaction
    
    async def issue_bonus(
        self,
        user_id: str,
        asset_type_code: str,
        amount: Decimal,
        idempotency_key: str,
        reason: str
    ) -> Transaction:
        """
        Issue bonus/incentive credits to user
        Money flows from System Bonus Pool to User Wallet
        """
        # Get asset type
        asset_type = await self._get_asset_type_by_code(asset_type_code)
        
        # Get or create user wallet
        user_wallet = await self._get_or_create_wallet(user_id, asset_type.id, is_system=False)
        
        # Get system bonus pool wallet
        bonus_wallet = await self._get_or_create_wallet(
            f"SYSTEM_BONUS_POOL_{asset_type_code}",
            asset_type.id,
            is_system=True
        )
        
        # Execute transaction
        metadata = {
            "bonus_reason": reason,
            "flow": "bonus"
        }
        
        transaction = await self._execute_transaction(
            from_wallet_id=bonus_wallet.id,
            to_wallet_id=user_wallet.id,
            asset_type_id=asset_type.id,
            amount=amount,
            transaction_type=TransactionType.BONUS,
            idempotency_key=idempotency_key,
            description=f"Bonus: {reason}",
            metadata=metadata
        )
        
        return transaction
    
    async def spend_credits(
        self,
        user_id: str,
        asset_type_code: str,
        amount: Decimal,
        idempotency_key: str,
        item_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Transaction:
        """
        Spend credits from user wallet (Purchase flow)
        Money flows from User Wallet to System Revenue
        """
        # Get asset type
        asset_type = await self._get_asset_type_by_code(asset_type_code)
        
        # Get user wallet
        stmt = select(Wallet).where(
            and_(
                Wallet.user_id == user_id,
                Wallet.asset_type_id == asset_type.id
            )
        )
        result = await self.db.execute(stmt)
        user_wallet = result.scalar_one_or_none()
        
        if not user_wallet:
            raise WalletNotFoundError(f"Wallet not found for user {user_id} and asset {asset_type_code}")
        
        # Get system revenue wallet
        revenue_wallet = await self._get_or_create_wallet(
            f"SYSTEM_REVENUE_{asset_type_code}",
            asset_type.id,
            is_system=True
        )
        
        # Execute transaction
        metadata = {
            "item_id": item_id,
            "flow": "spend"
        }
        
        transaction = await self._execute_transaction(
            from_wallet_id=user_wallet.id,
            to_wallet_id=revenue_wallet.id,
            asset_type_id=asset_type.id,
            amount=amount,
            transaction_type=TransactionType.SPEND,
            idempotency_key=idempotency_key,
            description=description or f"Purchase by {user_id}",
            metadata=metadata
        )
        
        return transaction
    
    async def get_wallet_balance(self, user_id: str, asset_type_code: str) -> Tuple[Wallet, AssetType]:
        """Get wallet balance for a user and asset type"""
        asset_type = await self._get_asset_type_by_code(asset_type_code)
        
        stmt = select(Wallet).where(
            and_(
                Wallet.user_id == user_id,
                Wallet.asset_type_id == asset_type.id
            )
        )
        result = await self.db.execute(stmt)
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            # Create wallet with zero balance if doesn't exist
            wallet = await self._get_or_create_wallet(user_id, asset_type.id)
            await self.db.commit()
        
        return wallet, asset_type
    
    async def get_transaction_history(
        self,
        user_id: str,
        asset_type_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Transaction]:
        """Get transaction history for a user"""
        # Get user wallets
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        
        if asset_type_code:
            asset_type = await self._get_asset_type_by_code(asset_type_code)
            stmt = stmt.where(Wallet.asset_type_id == asset_type.id)
        
        result = await self.db.execute(stmt)
        wallets = result.scalars().all()
        wallet_ids = [w.id for w in wallets]
        
        if not wallet_ids:
            return []
        
        # Get transactions involving these wallets
        stmt = select(Transaction).where(
            (Transaction.from_wallet_id.in_(wallet_ids)) |
            (Transaction.to_wallet_id.in_(wallet_ids))
        ).order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()
        
        return transactions

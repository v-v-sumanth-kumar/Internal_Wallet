from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging

from app.database import get_db
from app.schemas.wallet import (
    TopupRequest,
    BonusRequest,
    SpendRequest,
    TransactionResponse,
    WalletBalanceResponse,
)
from app.services.wallet_service import (
    WalletService,
    InsufficientFundsError,
    AssetTypeNotFoundError,
    WalletNotFoundError,
)
from app.utils.idempotency import generate_idempotency_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.post("/topup", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def topup_wallet(
    request: TopupRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Top-up user wallet (Purchase flow)
    
    User purchases credits using real money.
    Money flows from System Treasury to User Wallet.
    
    **Requires Idempotency-Key header to prevent duplicate charges**
    
    Example:
    ```
    POST /api/v1/wallets/topup
    Headers: {"Idempotency-Key": "purchase_user123_20260208_abc123"}
    Body: {
        "user_id": "user_123",
        "asset_type_code": "GOLD_COIN",
        "amount": 100.00,
        "payment_reference": "stripe_pi_xxx",
        "description": "Purchase 100 Gold Coins"
    }
    ```
    """
    service = WalletService(db)
    
    try:
        cached = await service._check_idempotency(
            idempotency_key=idempotency_key,
            request_path="/api/v1/wallets/topup",
            request_method="POST"
        )
        
        if cached:
            return cached["body"]
        
        transaction = await service.topup_wallet(
            user_id=request.user_id,
            asset_type_code=request.asset_type_code,
            amount=request.amount,
            idempotency_key=idempotency_key,
            payment_reference=request.payment_reference,
            description=request.description
        )
        
        response = TransactionResponse(
            transaction_id=transaction.transaction_id,
            transaction_type=transaction.transaction_type.value,
            status=transaction.status.value,
            from_wallet_id=transaction.from_wallet_id,
            to_wallet_id=transaction.to_wallet_id,
            amount=transaction.amount,
            description=transaction.description,
            created_at=transaction.created_at,
            completed_at=transaction.completed_at
        )
        
        await service._save_idempotency_log(
            idempotency_key=idempotency_key,
            request_path="/api/v1/wallets/topup",
            request_method="POST",
            response_status=201,
            response_body=response.model_dump(mode='json')
        )
        
        await db.commit()
        
        return response
    
    except AssetTypeNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Asset Type Not Found",
                "message": str(e),
                "user_id": request.user_id,
                "asset_type_code": request.asset_type_code
            }
        )
    except InsufficientFundsError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Insufficient Funds",
                "message": str(e),
                "user_id": request.user_id,
                "asset_type_code": request.asset_type_code
            }
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Topup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Transaction Failed",
                "message": f"Transaction failed: {str(e)}",
                "type": type(e).__name__
            }
        )


@router.post("/bonus", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def issue_bonus(
    request: BonusRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Issue bonus/incentive credits to user
    
    System issues free credits to user (e.g., referral bonus, promo).
    Money flows from System Bonus Pool to User Wallet.
    
    **Requires Idempotency-Key header to prevent duplicate bonuses**
    
    Example:
    ```
    POST /api/v1/wallets/bonus
    Headers: {"Idempotency-Key": "bonus_user123_referral_abc123"}
    Body: {
        "user_id": "user_123",
        "asset_type_code": "GOLD_COIN",
        "amount": 50.00,
        "reason": "Referral bonus - invited 5 friends"
    }
    ```
    """
    service = WalletService(db)
    
    try:
        cached = await service._check_idempotency(
            idempotency_key=idempotency_key,
            request_path="/api/v1/wallets/bonus",
            request_method="POST"
        )
        
        if cached:
            return cached["body"]
        
        transaction = await service.issue_bonus(
            user_id=request.user_id,
            asset_type_code=request.asset_type_code,
            amount=request.amount,
            idempotency_key=idempotency_key,
            reason=request.reason
        )
        
        response = TransactionResponse(
            transaction_id=transaction.transaction_id,
            transaction_type=transaction.transaction_type.value,
            status=transaction.status.value,
            from_wallet_id=transaction.from_wallet_id,
            to_wallet_id=transaction.to_wallet_id,
            amount=transaction.amount,
            description=transaction.description,
            created_at=transaction.created_at,
            completed_at=transaction.completed_at
        )
        
        await service._save_idempotency_log(
            idempotency_key=idempotency_key,
            request_path="/api/v1/wallets/bonus",
            request_method="POST",
            response_status=201,
            response_body=response.model_dump(mode='json')
        )
        
        await db.commit()
        
        return response
    
    except AssetTypeNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Asset Type Not Found",
                "message": str(e),
                "user_id": request.user_id,
                "asset_type_code": request.asset_type_code
            }
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Bonus failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Transaction Failed",
                "message": f"Transaction failed: {str(e)}",
                "type": type(e).__name__
            }
        )


@router.post("/spend", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def spend_credits(
    request: SpendRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Spend credits from user wallet (Purchase flow)
    
    User spends credits to buy items/services in the app.
    Money flows from User Wallet to System Revenue.
    
    **Requires Idempotency-Key header to prevent duplicate charges**
    
    Example:
    ```
    POST /api/v1/wallets/spend
    Headers: {"Idempotency-Key": "spend_user123_item456_abc123"}
    Body: {
        "user_id": "user_123",
        "asset_type_code": "GOLD_COIN",
        "amount": 30.00,
        "item_id": "item_456",
        "description": "Purchase premium skin"
    }
    ```
    """
    service = WalletService(db)
    
    try:
        cached = await service._check_idempotency(
            idempotency_key=idempotency_key,
            request_path="/api/v1/wallets/spend",
            request_method="POST"
        )
        
        if cached:
            return cached["body"]
        
        transaction = await service.spend_credits(
            user_id=request.user_id,
            asset_type_code=request.asset_type_code,
            amount=request.amount,
            idempotency_key=idempotency_key,
            item_id=request.item_id,
            description=request.description
        )
        
        response = TransactionResponse(
            transaction_id=transaction.transaction_id,
            transaction_type=transaction.transaction_type.value,
            status=transaction.status.value,
            from_wallet_id=transaction.from_wallet_id,
            to_wallet_id=transaction.to_wallet_id,
            amount=transaction.amount,
            description=transaction.description,
            created_at=transaction.created_at,
            completed_at=transaction.completed_at
        )
        
        await service._save_idempotency_log(
            idempotency_key=idempotency_key,
            request_path="/api/v1/wallets/spend",
            request_method="POST",
            response_status=201,
            response_body=response.model_dump(mode='json')
        )
        
        await db.commit()
        
        return response
    
    except AssetTypeNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Asset Type Not Found",
                "message": str(e),
                "user_id": request.user_id,
                "asset_type_code": request.asset_type_code
            }
        )
    except WalletNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Wallet Not Found",
                "message": str(e),
                "user_id": request.user_id,
                "asset_type_code": request.asset_type_code
            }
        )
    except InsufficientFundsError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Insufficient Funds",
                "message": str(e),
                "user_id": request.user_id,
                "requested_amount": str(request.amount)
            }
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Spend failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Transaction Failed",
                "message": f"Transaction failed: {str(e)}",
                "type": type(e).__name__
            }
        )


@router.get("/{user_id}/balance", response_model=WalletBalanceResponse)
async def get_wallet_balance(
    user_id: str,
    asset_type_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get wallet balance for a user and asset type
    
    Example:
    ```
    GET /api/v1/wallets/user_123/balance?asset_type_code=GOLD_COIN
    ```
    """
    service = WalletService(db)
    
    try:
        wallet, asset_type = await service.get_wallet_balance(user_id, asset_type_code)
        
        return WalletBalanceResponse(
            wallet_id=wallet.id,
            user_id=wallet.user_id,
            asset_type_code=asset_type.code,
            balance=wallet.balance,
            is_system=wallet.is_system,
            updated_at=wallet.updated_at
        )
    
    except AssetTypeNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Asset Type Not Found",
                "message": str(e),
                "user_id": user_id,
                "asset_type_code": asset_type_code
            }
        )
    except Exception as e:
        logger.error(f"Get balance failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to Get Balance",
                "message": str(e),
                "type": type(e).__name__
            }
        )


@router.get("/{user_id}/transactions", response_model=List[TransactionResponse])
async def get_transaction_history(
    user_id: str,
    asset_type_code: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Get transaction history for a user
    
    Example:
    ```
    GET /api/v1/wallets/user_123/transactions?asset_type_code=GOLD_COIN&limit=20
    ```
    """
    service = WalletService(db)
    
    try:
        transactions = await service.get_transaction_history(
            user_id=user_id,
            asset_type_code=asset_type_code,
            limit=min(limit, 100),  
            offset=offset
        )
        
        return [
            TransactionResponse(
                transaction_id=t.transaction_id,
                transaction_type=t.transaction_type.value,
                status=t.status.value,
                from_wallet_id=t.from_wallet_id,
                to_wallet_id=t.to_wallet_id,
                amount=t.amount,
                description=t.description,
                created_at=t.created_at,
                completed_at=t.completed_at
            )
            for t in transactions
        ]
    
    except AssetTypeNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Asset Type Not Found",
                "message": str(e),
                "user_id": user_id,
                "asset_type_code": asset_type_code if asset_type_code else "N/A"
            }
        )
    except Exception as e:
        logger.error(f"Get transactions failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to Get Transactions",
                "message": str(e),
                "type": type(e).__name__
            }
        )

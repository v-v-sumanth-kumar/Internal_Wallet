"""Database Seed Script - Populates initial data"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from decimal import Decimal

from app.database import AsyncSessionLocal, engine, Base
from app.models import AssetType, Wallet
from app.config import settings


async def seed_database():
    """Seed the database with initial data"""
    print("=" * 60)
    print("DATABASE SEEDING STARTED")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if data already exists
            result = await session.execute(select(AssetType))
            existing_assets = result.scalars().all()
            
            if existing_assets:
                print("\n⚠️  Database already seeded. Skipping...")
                return
            
            print("\n1️⃣  Creating Asset Types...")
            
            # Define asset types
            asset_types = [
                {
                    "code": "GOLD_COIN",
                    "name": "Gold Coins",
                    "description": "Primary in-game currency for purchasing items and services",
                    "is_active": True
                },
                {
                    "code": "DIAMOND",
                    "name": "Diamonds",
                    "description": "Premium currency for exclusive items and features",
                    "is_active": True
                },
                {
                    "code": "LOYALTY_POINT",
                    "name": "Loyalty Points",
                    "description": "Reward points earned through gameplay and activities",
                    "is_active": True
                },
            ]
            
            created_assets = {}
            for asset_data in asset_types:
                asset = AssetType(**asset_data)
                session.add(asset)
                await session.flush()
                created_assets[asset.code] = asset
                print(f"   ✓ Created: {asset.name} ({asset.code})")
            
            print("\n2️⃣  Creating System Wallets...")
            
            # Create system wallets for each asset type
            system_wallets = []
            for code, asset in created_assets.items():
                # Treasury wallet (source for top-ups)
                treasury = Wallet(
                    user_id=f"SYSTEM_TREASURY_{code}",
                    asset_type_id=asset.id,
                    balance=Decimal("999999999.00"),  # Unlimited supply for virtual currency
                    is_system=True,
                    version=0
                )
                session.add(treasury)
                system_wallets.append(treasury)
                print(f"   ✓ Created Treasury wallet for {asset.name}")
                
                # Bonus pool wallet (source for bonuses)
                bonus_pool = Wallet(
                    user_id=f"SYSTEM_BONUS_POOL_{code}",
                    asset_type_id=asset.id,
                    balance=Decimal("999999999.00"),
                    is_system=True,
                    version=0
                )
                session.add(bonus_pool)
                system_wallets.append(bonus_pool)
                print(f"   ✓ Created Bonus Pool wallet for {asset.name}")
                
                # Revenue wallet (destination for user spending)
                revenue = Wallet(
                    user_id=f"SYSTEM_REVENUE_{code}",
                    asset_type_id=asset.id,
                    balance=Decimal("0.00"),
                    is_system=True,
                    version=0
                )
                session.add(revenue)
                system_wallets.append(revenue)
                print(f"   ✓ Created Revenue wallet for {asset.name}")
            
            await session.flush()
            
            print("\n3️⃣  Creating Test User Wallets...")
            
            # Create test users with initial balances
            test_users = [
                {
                    "user_id": "user_alice",
                    "balances": {
                        "GOLD_COIN": Decimal("1000.00"),
                        "DIAMOND": Decimal("50.00"),
                        "LOYALTY_POINT": Decimal("500.00"),
                    }
                },
                {
                    "user_id": "user_bob",
                    "balances": {
                        "GOLD_COIN": Decimal("750.00"),
                        "DIAMOND": Decimal("25.00"),
                        "LOYALTY_POINT": Decimal("300.00"),
                    }
                },
                {
                    "user_id": "user_charlie",
                    "balances": {
                        "GOLD_COIN": Decimal("2500.00"),
                        "DIAMOND": Decimal("100.00"),
                        "LOYALTY_POINT": Decimal("1200.00"),
                    }
                },
            ]
            
            for user_data in test_users:
                user_id = user_data["user_id"]
                print(f"\n   👤 User: {user_id}")
                
                for code, balance in user_data["balances"].items():
                    asset = created_assets[code]
                    wallet = Wallet(
                        user_id=user_id,
                        asset_type_id=asset.id,
                        balance=balance,
                        is_system=False,
                        version=0
                    )
                    session.add(wallet)
                    print(f"      ✓ {asset.name}: {balance}")
            
            # Commit all changes
            await session.commit()
            
            print("\n" + "=" * 60)
            print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY")
            print("=" * 60)
            
            # Print summary
            print("\n📊 SUMMARY:")
            print(f"   • Asset Types: {len(asset_types)}")
            print(f"   • System Wallets: {len(system_wallets)}")
            print(f"   • Test Users: {len(test_users)}")
            print(f"   • User Wallets: {len(test_users) * len(asset_types)}")
            
            print("\n🎮 TEST USERS:")
            for user_data in test_users:
                user_id = user_data["user_id"]
                print(f"   • {user_id}")
                for code, balance in user_data["balances"].items():
                    print(f"     - {created_assets[code].name}: {balance}")
            
            print("\n💡 NEXT STEPS:")
            print("   1. Start the API server: uvicorn app.main:app --reload")
            print("   2. Visit: http://localhost:8000/docs")
            print("   3. Test the endpoints with the test users above")
            
            print("\n📝 SAMPLE API REQUESTS:")
            print("   • Get Balance:")
            print("     GET /api/v1/wallets/user_alice/balance?asset_type_code=GOLD_COIN")
            print("\n   • Top-up Wallet:")
            print("     POST /api/v1/wallets/topup")
            print("     Header: Idempotency-Key: topup_alice_001")
            print("     Body: {\"user_id\": \"user_alice\", \"asset_type_code\": \"GOLD_COIN\", \"amount\": 100}")
            print("\n   • Spend Credits:")
            print("     POST /api/v1/wallets/spend")
            print("     Header: Idempotency-Key: spend_alice_001")
            print("     Body: {\"user_id\": \"user_alice\", \"asset_type_code\": \"GOLD_COIN\", \"amount\": 50}")
            
            print("\n" + "=" * 60)
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ ERROR during seeding: {str(e)}")
            raise


async def main():
    """Main entry point"""
    try:
        await seed_database()
    except Exception as e:
        print(f"\n❌ Seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""Main FastAPI Application"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db, close_db
from app.api.v1.wallets import router as wallet_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Internal Wallet Service...")
    logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'N/A'}")
    yield
    # Shutdown
    logger.info("Shutting down Internal Wallet Service...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Internal Wallet Service API
    
    A high-performance wallet service for managing application-specific virtual currencies.
    
    ## Features
    
    * **Topup**: Purchase credits using real money
    * **Bonus**: Issue free credits (referral bonuses, promotions)
    * **Spend**: Spend credits within the application
    * **Balance Check**: Get current wallet balance
    * **Transaction History**: View past transactions
    
    ## Key Characteristics
    
    * **ACID Compliance**: All transactions are atomic and consistent
    * **Concurrency Safe**: Uses pessimistic locking to prevent race conditions
    * **Idempotent**: Duplicate requests return cached responses
    * **Double-Entry Ledger**: Complete audit trail of all transactions
    * **Deadlock Prevention**: Locks acquired in consistent order
    
    ## Idempotency
    
    All mutation endpoints require an `Idempotency-Key` header.
    Use a unique key per logical request (e.g., `purchase_user123_20260208_abc123`).
    
    If the same key is used again within 24 hours, the cached response is returned
    without processing the request again.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "error": str(exc) if settings.DEBUG else "Internal Server Error"
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "documentation": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(wallet_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

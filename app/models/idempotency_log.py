from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class IdempotencyLog(Base):
    """Idempotency Log Model
    
    Stores idempotency keys and their responses to prevent duplicate processing
    When a request comes in with a key that already exists, return the stored response
    """
    __tablename__ = "idempotency_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True)
    
    request_path = Column(String(255), nullable=False)
    request_method = Column(String(10), nullable=False)
    
    response_status = Column(Integer)
    response_body = Column(String(5000))  
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  
    
    __table_args__ = (
        Index('idx_idempotency_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<IdempotencyLog(id={self.id}, key='{self.idempotency_key}')>"

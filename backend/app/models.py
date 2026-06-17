from sqlalchemy import Column, String, Integer, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Product(Base):
    __tablename__ = "products"
    
    product_id = Column(String(50), primary_key=True, index=True)
    product_name = Column(String(150), nullable=False)
    brand = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    sub_category = Column(String(100), nullable=False)
    pack_size_ml = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    sales = relationship("Sale", back_populates="product")
    inventory = relationship("Inventory", back_populates="product")

class Store(Base):
    __tablename__ = "stores"
    
    store_id = Column(String(50), primary_key=True, index=True)
    store_name = Column(String(150), nullable=False)
    region = Column(String(50), nullable=False)
    city = Column(String(100), nullable=False)
    store_format = Column(String(100), nullable=False)

    sales = relationship("Sale", back_populates="store")
    inventory = relationship("Inventory", back_populates="store")

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    week_start_date = Column(Date, nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    store_id = Column(String(50), ForeignKey("stores.store_id"), nullable=False)
    region = Column(String(50), nullable=False, index=True)
    units_sold = Column(Integer, nullable=False)
    revenue = Column(Float, nullable=False)
    promotion_flag = Column(Boolean, nullable=False, index=True)
    promotion_type = Column(String(50), nullable=True)
    discount_pct = Column(Float, nullable=False, default=0.0)

    product = relationship("Product", back_populates="sales")
    store = relationship("Store", back_populates="sales")

class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    week_start_date = Column(Date, nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    store_id = Column(String(50), ForeignKey("stores.store_id"), nullable=False)
    opening_stock = Column(Integer, nullable=False)
    units_received = Column(Integer, nullable=False)
    units_sold = Column(Integer, nullable=False)
    closing_stock = Column(Integer, nullable=False)
    stockout_flag = Column(Boolean, nullable=False, default=False, index=True)

    product = relationship("Product", back_populates="inventory")
    store = relationship("Store", back_populates="inventory")

# Chat memory tables
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    session_id = Column(String(100), primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.session_id"), nullable=False)
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    sql_queries = Column(Text, nullable=True)  # Store generated SQL (if any)
    query_results = Column(Text, nullable=True)  # Store query output as JSON string
    chart_type = Column(String(50), nullable=True)  # "trend", "comparison", "distribution", "text", etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")

# System Evaluation metrics
class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_query = Column(String(500), nullable=False)
    sql_generated = Column(Text, nullable=True)
    sql_success = Column(Boolean, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    is_empty_result = Column(Boolean, nullable=False)
    user_satisfaction = Column(Integer, nullable=True)  # 1-5 rating or thumbs up (1) / down (0)

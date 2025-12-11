from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, Enum as SQLEnum, ForeignKey, JSON, Index
from sqlalchemy.sql import func
import enum
from app.database import Base


class ModelType(str, enum.Enum):
    """AI model type"""
    ETA = "eta"
    OCCUPATION = "occupation"
    CONFLIT = "conflit"


class AIPrediction(Base):
    """
    AI prediction history model.
    Stores all AI model predictions for auditing and analysis.
    """
    __tablename__ = "ai_predictions"
    
    # Primary key
    prediction_id = Column(Integer, primary_key=True, autoincrement=True, doc="Unique prediction ID")
    
    # Foreign key
    flight_icao24 = Column(String(6), ForeignKey("flights.icao24"), nullable=False, index=True, doc="Related flight")
    
    # Model information
    model_type = Column(SQLEnum(ModelType), nullable=False, index=True, doc="Type of AI model")
    model_version = Column(String(20), default="1.0.0", doc="Model version used")
    
    # Input/Output data (stored as JSON)
    input_data = Column(JSON, nullable=False, doc="Input parameters sent to model")
    output_data = Column(JSON, nullable=False, doc="Prediction results from model")
    
    # Cache information and metrics (match migration schema)
    cached = Column(Boolean, default=False, doc="Whether result came from cache")
    execution_time_ms = Column(Integer, nullable=True, doc="Prediction latency in milliseconds")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), doc="Prediction timestamp")
    
    # Indexes
    __table_args__ = (
        Index('idx_prediction_flight_model', 'flight_icao24', 'model_type'),
        Index('idx_prediction_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AIPrediction(id={self.prediction_id}, flight={self.flight_icao24}, model={self.model_type})>"

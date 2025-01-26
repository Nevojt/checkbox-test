from sqlalchemy import Column, String, Float, ForeignKey, JSON
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship

from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.database.async_connect import Base

class Products(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'), nullable=False)
    receipt_id = Column(UUID, ForeignKey("receipts.id"))
    name = Column(String, index=True)
    price = Column(Float)
    quantity = Column(Float)
    total = Column(Float)
    receipt = relationship("Receipt", back_populates="products")

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('uuid_generate_v4()'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    total = Column(Float)
    rest = Column(Float)
    payment_type = Column(String)
    payment_amount = Column(Float)
    recept_url = Column(String)
    products = relationship("Products", back_populates="receipt")


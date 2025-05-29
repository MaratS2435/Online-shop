from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Integer, Numeric, ForeignKey, Boolean, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_in_stock: Mapped[int] = mapped_column(Integer, default=0)
    seller_id: Mapped[int] = mapped_column(Integer, ForeignKey("sellers.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    seller = relationship("Seller", back_populates="products")


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="seller", cascade="all, delete-orphan")
from sqlalchemy import String, Integer, Numeric, ForeignKey, Boolean, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    seller_id: Mapped[int] = mapped_column(Integer, ForeignKey("sellers.id"), nullable=False)
    created_at: Mapped[func.now()] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    seller = relationship("Seller", back_populates="products")


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    products = relationship("Product", back_populates="seller", cascade="all, delete-orphan")
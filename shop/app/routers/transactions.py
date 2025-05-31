from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.dependencies import get_current_user
from app.database import get_session
from app.models.auth import User
from app.models.product import Product
from app.models.transactions import Transaction
from app.schemas.transactions import (
    TransactionRead,
    DepositCreate,
    PurchaseCreate
)
from app.schemas.review import TokenData

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post(
    "/deposit",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED
)
async def deposit(
    data: DepositCreate,
    current_user: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    async with session.begin():
        user = await session.scalar(select(User).where(User.id == current_user.user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.balance += data.amount
        transaction = Transaction(
            user_id=current_user.user_id,
            amount=data.amount,
            type="deposit"
        )
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction)

    return transaction


@router.post(
    "/purchase",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED
)
async def purchase(
    data: PurchaseCreate,
    current_user: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    async with session.begin():
        user = await session.scalar(select(User).where(User.id == current_user.user_id))
        product = await session.scalar(select(Product).where(Product.id == data.product_id))

        if not user or not product:
            raise HTTPException(status_code=404, detail="User or product not found")

        if product.user_id == current_user.user_id:
            raise HTTPException(status_code=400, detail="Cannot purchase your own product")

        if product.quantity_in_stock < data.quantity:
            raise HTTPException(status_code=400, detail="Not enough stock")

        total_cost = product.price * data.quantity
        if user.balance < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        seller = await session.scalar(select(User).where(User.id == product.user_id))
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")

        user.balance -= total_cost
        seller.balance += total_cost
        product.quantity_in_stock -= data.quantity

        transaction = Transaction(
            user_id=current_user.user_id,
            amount=-total_cost,
            type="purchase",
            product_id=data.product_id
        )
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction)

    return transaction


@router.get(
    "/history",
    response_model=list[TransactionRead]
)
async def get_transaction_history(
    current_user: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Transaction).where(Transaction.user_id == current_user.user_id))
    return result.scalars().all()
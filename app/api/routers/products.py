from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Query
from app.schemas import  products
from app.api.deps import SessionDep, CurrentUser
from app.models.products import Receipt, Products
from app.core import crud

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload


router = APIRouter()

@router.post("/receipts/", response_model=products.ReceiptOutput)
async def create_receipt(*, session: SessionDep, current_user: CurrentUser,
                         receipt_input: products.ReceiptInput,
                         ) -> Any:
    try:
       total = 0
       products_data = []
       for product in receipt_input.products:
           product_total = product.price * product.quantity
           total += product_total
           product_data = products.ProductOutput(
               name=product.name,
               price=product.price,
               quantity=product.quantity,
               total=product_total
           )
           products_data.append(product_data)

       rest = round(receipt_input.payment.amount - total, 2)
       if rest < 0:
           raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

       receipt = Receipt(
           user_id=current_user.id,
           total=total,
           rest=rest,
           payment=receipt_input.payment.model_dump()
       )
       session.add(receipt)
       await session.commit()
       await session.refresh(receipt)

       for product_data in products_data:
           product = Products(
               receipt_id=receipt.id,
               name=product_data.name,
               price=product_data.price,
               quantity=product_data.quantity,
               total=product_data.total
           )
           session.add(product)
       await session.commit()

       response = products.ReceiptOutput(
           id=receipt.id,
           products=products_data,
           payment=receipt_input.payment,
           total=receipt.total,
           rest=receipt.rest,
           created_at=receipt.created_at
       )

    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    return response

@router.get("/receipts/", response_model=List[products.ReceiptSummary])
async def get_all_receipts(*, session: SessionDep,
                           current_user: CurrentUser,
                           offset: int = 0,
                           limit: int = 10,
                           min_total: Optional[float] = Query(None),
                           max_total: Optional[float] = Query(None),
                           payment_type: Optional[str] = Query(None),
                           start_date: Optional[datetime] = Query(None),
                           end_date: Optional[datetime] = Query(None)
                           ) -> Any:
    try:
        query = select(Receipt).where(Receipt.user_id == current_user.id)

        if min_total is not None:
            query = query.where(Receipt.total >= min_total)
        if max_total is not None:
            query = query.where(Receipt.total <= max_total)
        if payment_type is not None:
            query = query.where(Receipt.payment["type"].astext == payment_type)
        if start_date is not None:
            query = query.where(Receipt.created_at >= start_date)
        if end_date is not None:
            query = query.where(Receipt.created_at <= end_date)

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        receipts = result.scalars().all()

        return [
            products.ReceiptSummary(
                id=receipt.id,
                created_at=receipt.created_at,
                total=receipt.total,
                payment=receipt.payment
            ) for receipt in receipts
        ]

    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get("/receipts/{receipt_id}/", response_model=products.ReceiptOutput)
async def get_receipt(receipt_id: UUID, current_user: CurrentUser, session: SessionDep):
    query = select(Receipt).options(selectinload(Receipt.products)).where(Receipt.id == receipt_id,
                                  Receipt.user_id == current_user.id)
    result = await session.execute(query)
    receipt = result.scalars().first()

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    products_list = [
        products.ProductOutput(
            name=product.name,
            price=product.price,
            quantity=product.quantity,
            total=product.total
        ) for product in receipt.products
    ]

    return products.ReceiptOutput(
        id=receipt.id,
        products=products_list,
        payment=receipt.payment,
        total=receipt.total,
        rest=receipt.rest,
        created_at=receipt.created_at
    )

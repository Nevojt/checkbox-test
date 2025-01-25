from typing import Any

from fastapi import APIRouter, HTTPException, status
from app.schemas import  products
from app.api.deps import SessionDep, CurrentUser
from app.models.products import Receipt, Products
from app.core import crud


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


    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return response


from pydantic import BaseModel, UUID4, Strict, Field, ConfigDict
from typing import List, Annotated
from datetime import datetime


class ProductInput(BaseModel):
    name: str
    price: float
    quantity: float

class ReceiptInput(BaseModel):
    products: List[ProductInput]
    payment_type: str
    payment_amount: float

class ProductOutput(BaseModel):
    name: str
    price: float
    quantity: float
    total: float

class ReceiptPayment(BaseModel):
    type: str
    amount: float

class ReceiptOutput(BaseModel):
    id: Annotated[UUID4, Strict(False)]
    products: List[ProductOutput]
    payment: ReceiptPayment
    total: float
    rest: float
    created_at: datetime

# class ReceiptSummary(BaseModel):
#     id: Annotated[UUID4, Strict(False)]
#     created_at: datetime
#     total: float
#     payment: PaymentInput
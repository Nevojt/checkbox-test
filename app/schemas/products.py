from pydantic import BaseModel, UUID4, Strict, Field, ConfigDict
from typing import List, Annotated
from datetime import datetime


class ProductInput(BaseModel):
    name: str
    price: float
    quantity: float

class PaymentInput(BaseModel):
    type: str = Field(..., pattern="^(cash|cashless)$")
    amount: float

class ReceiptInput(BaseModel):
    products: List[ProductInput]
    payment: PaymentInput

class ProductOutput(ProductInput):
    total: float

class ReceiptOutput(BaseModel):
    id: Annotated[UUID4, Strict(False)]
    products: List[ProductOutput]
    payment: PaymentInput
    total: float
    rest: float
    created_at: datetime

class ReceiptSummary(BaseModel):
    id: Annotated[UUID4, Strict(False)]
    created_at: datetime
    total: float
    payment: PaymentInput
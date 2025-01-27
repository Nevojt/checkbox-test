import os
from datetime import datetime
from typing import Any, Optional, Dict
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import  products
from app.api.deps import SessionDep, CurrentUser
from app.models.products import Receipt, Products
from app.core.utils import upload_to_backblaze

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import cast, String, func

router = APIRouter()

@router.post("/receipts/", response_model=products.ReceiptOutput)
async def create_receipt(*, session: SessionDep, current_user: CurrentUser,
                         receipt_input: products.ReceiptInput,
                         ) -> Any:
    """
    POST /receipts/
    Опис: Створює новий чек для користувача.
    Вхідні параметри:
    - `receipt_input` (об'єкт JSON):
        - `products` (список об'єктів): перелік товарів, що включає:
            - `name` (str): Назва товару.
            - `price` (float): Ціна за одиницю товару.
            - `quantity` (int): Кількість товару.
        - `payment_type` (str): Тип оплати ("cash" або "card").
        - `payment_amount` (float): Сума оплати.
    Вихідні дані:
    - Об'єкт JSON, що містить:
        - `id` (UUID): Унікальний ідентифікатор чека.
        - `products`: Інформація про товари в чеку.
        - `payment`: Інформація про оплату.
        - `total` (float): Загальна сума чека.
        - `rest` (float): Решта (здача).
        - `created_at` (datetime): Час створення чека.
        - `recept_url` (str): URL чека."""
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

       rest = round(receipt_input.payment_amount - total, 2)
       if rest < 0:
           raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

       receipt = Receipt(
           user_id=current_user.id,
           total=round(total, 2),
           rest=rest,
           payment_type=receipt_input.payment_type,
           payment_amount=receipt_input.payment_amount
       )
       session.add(receipt)
       await session.commit()
       await session.refresh(receipt)

       # Create product entries
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

       recept_url = await get_receipt_text_url(session=session, receipt_id=receipt.id, line_width=32)
       # Prepare response
       response = products.ReceiptOutput(
           id=receipt.id,
           products=products_data,
           payment=products.ReceiptPayment(
               type=receipt_input.payment_type,
               amount=receipt_input.payment_amount
           ),
           total=round(total, 2),
           rest=rest,
           created_at=receipt.created_at,
           recept_url=recept_url
       )


    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    return response

@router.get("/receipts/", response_model=Dict[str, Any])
async def get_all_receipts(*, session: SessionDep,
                           current_user: CurrentUser,
                           offset: int = 0,
                           limit: int = 10,
                           min_total: Optional[float] = Query(None),
                           max_total: Optional[float] = Query(None),
                           payment_type: Optional[str] = Query(None),
                           start_date: Optional[datetime] = Query(None, description="Format: YYYY-MM-DDTHH:MM:SS"),
                           end_date: Optional[datetime] = Query(None, description="Format: YYYY-MM-DDTHH:MM:SS")) -> Any:
    """
    GET /receipts/
    Опис: Повертає список чеків для аутентифікованого користувача з можливістю фільтрації.
    Вхідні параметри:
    - `offset` (int, опціонально): Кількість чеків для пропуску (пагінація).
    - `limit` (int, опціонально): Максимальна кількість чеків, яку потрібно повернути.
    - `min_total` (float, опціонально): Мінімальна загальна сума чека.
    - `max_total` (float, опціонально): Максимальна загальна сума чека.
    - `payment_type` (str, опціонально): Тип оплати ("cash" або "card").
    - `start_date` (datetime, опціонально): Початкова дата створення.
    - `end_date` (datetime, опціонально): Кінцева дата створення.
    Вихідні дані:
    - Словник, що містить:
        - `total_count` (int): Загальна кількість чеків.
        - `items`: Список чеків у форматі JSON."""
    try:
        query = select(Receipt).options(selectinload(Receipt.products)).where(Receipt.user_id == current_user.id)

        if min_total is not None:
            query = query.where(Receipt.total >= min_total)
        if max_total is not None:
            query = query.where(Receipt.total <= max_total)
        if payment_type is not None:
            query = query.where(cast(Receipt.payment["type"], String) == payment_type)
        if start_date is not None:
            query = query.where(Receipt.created_at >= start_date)
        if end_date is not None:
            query = query.where(Receipt.created_at <= end_date)

        # Correcting with_only_columns to use positional arguments
        total_query = query.with_only_columns(func.count())
        total_count = await session.execute(total_query)
        total_count = total_count.scalar()

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        receipts = result.scalars().all()

        return {
            "total_count": total_count,
            "items": [
                products.ReceiptOutput(
                    id=receipt.id,
                    products=[
                        products.ProductOutput(
                            name=product.name,
                            price=product.price,
                            quantity=product.quantity,
                            total=product.total
                        ) for product in receipt.products
                    ],
                    payment=products.ReceiptPayment(
                        type=receipt.payment_type,
                        amount=receipt.payment_amount
                    ),
                    total=receipt.total,
                    rest=receipt.rest,
                    created_at=receipt.created_at,
                    recept_url=receipt.recept_url
                ) for receipt in receipts
            ]
        }

    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get("/receipts/{receipt_id}/", response_model=products.ReceiptOutput)
async def get_receipt(receipt_id: UUID, current_user: CurrentUser, session: SessionDep):
    """
    GET / receipts / {receipt_id} /
    Опис: Повертає чек за його унікальним ідентифікатором.
    Вхідні параметри:
    - `receipt_id` (UUID): Унікальний ідентифікатор чека.
    Вихідні дані:
    - Об'єкт JSON, що містить інформацію про чек:
        - `id` (UUID): Унікальний ідентифікатор.
        - `products`: Перелік товарів.
        - `payment`: Деталі оплати.
        - `total` (float): Загальна сума.
        - `rest` (float): Решта.
        - `created_at` (datetime): Дата створення.
        - `recept_url` (str): URL чека."""
    try:
        query = select(Receipt).options(selectinload(Receipt.products)).where(Receipt.id == receipt_id,
                                      Receipt.user_id == current_user.id)
        result = await session.execute(query)
        receipt = result.scalars().first()

        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")

        return products.ReceiptOutput(
            id=receipt.id,
            products=[products.ProductOutput(
                    name=product.name,
                    price=product.price,
                    quantity=product.quantity,
                    total=product.total
                        ) for product in receipt.products
                    ],
            payment=products.ReceiptPayment(
                    type=receipt.payment_type,
                    amount=receipt.payment_amount
                    ),
            total=receipt.total,
            rest=receipt.rest,
            created_at=receipt.created_at,
            recept_url=receipt.recept_url
        )
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))

@router.get("/receipts/{receipt_id}/file-url")
async def get_receipt_file_url(receipt_id: UUID, session: SessionDep):
    """
    GET /receipts/{receipt_id}/file-url
    Опис: Повертає URL, який веде на текстову версію чека.
    Вхідні параметри:
    - `receipt_id` (UUID): Унікальний ідентифікатор чека.
    Вихідні дані:
    - `recept_url` (str): URL, за яким можна завантажити текстову версію чека.
    Помилки:
    - **404 Not Found**: Чек із вказаним `receipt_id` не знайдено.
    - **500 Internal Server Error**: Виникла внутрішня помилка сервера."""
    try:
        query = select(Receipt).where(Receipt.id == receipt_id)
        result = await session.execute(query)
        receipt = result.scalars().first()

        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")

        return receipt.recept_url
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))

@router.get("/receipts/{receipt_id}/text")
async def get_receipt_text_version(*, session: SessionDep, receipt_id: UUID, line_width: int = 32):
    """
    GET / receipts / {receipt_id} / text
    Опис: Генерує текстову версію чека в стилі касового чека.
    Вхідні параметри:
    - `receipt_id` (UUID): Унікальний ідентифікатор чека.
    - `line_width` (int, опціонально): Ширина рядка тексту (за замовчуванням 32 символи).
    Вихідні дані:
    - Tекстовий файл з чеком"""
    lines, _ = await create_receipt_text(session=session, receipt_id=receipt_id, line_width=line_width)
    return lines


async def create_receipt_text(*, session: AsyncSession, receipt_id: UUID, line_width: int):
    try:
        query = select(Receipt).options(selectinload(Receipt.products)).where(Receipt.id == receipt_id)
        result = await session.execute(query)
        receipt = result.scalars().first()

        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")

        lines = []
        lines.append("ФОП Джонсонюк Борис".center(line_width, ' '))
        lines.append("=" * line_width)

        for index, product in enumerate(receipt.products):
            quantity_price = f"{product.quantity:.2f} x {product.price:.2f}"
            total_price = f"{product.total:.2f}"

            for wrapped_line in split_long_words(product.name, line_width):
                lines.append(wrapped_line)

            spaces = line_width - len(quantity_price) - len(total_price)
            lines.append(f"{quantity_price}{' ' * spaces}{total_price}")

            if index < len(receipt.products) - 1:
                lines.append("-" * line_width)

        lines.append("=" * line_width)

        total_line = f"СУМА{' ' * (line_width - len('СУМА') - len(f'{receipt.total:.2f}'))}{receipt.total:.2f}"
        lines.append(total_line)

        payment_type = "Готівка" if receipt.payment_type == "cash" else "Картка"
        payment_line = f"{payment_type}{' ' * (line_width - len(payment_type) - len(f'{receipt.payment_amount:.2f}'))}{receipt.payment_amount:.2f}"
        lines.append(payment_line)

        rest_line = f"Решта{' ' * (line_width - len('Решта') - len(f'{receipt.rest:.2f}'))}{receipt.rest:.2f}"
        lines.append(rest_line)

        lines.append("=" * line_width)
        lines.append(receipt.created_at.strftime("%d.%m.%Y %H:%M").center(line_width, ' '))
        lines.append("Дякуємо за покупку!".center(line_width, ' '))

        return lines, receipt
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))

def check_params(params):
    return len(f"{int(params):.2f}") + 1

def split_long_words(text, line_width):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= line_width:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

async def save_receipt_to_file(lines, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))

async def get_receipt_text_url(*, session: SessionDep, receipt_id: UUID, line_width: int = 32):
    try:
        lines, receipt = await create_receipt_text(session=session, receipt_id=receipt_id, line_width=line_width)
        if receipt.recept_url is None:
            await save_receipt_to_file(lines, "app/checks/" + str(receipt_id))
            check = await upload_to_backblaze("app/checks/" + str(receipt_id), str(receipt_id))
            receipt.recept_url = check
            session.add(receipt)
            await session.commit()
        else:
            check = receipt.recept_url

        return check
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))


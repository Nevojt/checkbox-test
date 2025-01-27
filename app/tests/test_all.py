
import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from faker import Faker
from fastapi.testclient import TestClient

faker = Faker()

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_user_create():
    return {
        "username": faker.user_name(),
        "email": faker.email(),
        "password": faker.password(),
    }


@pytest.mark.asyncio
async def test_create_user(test_user_create):
    with TestClient(app) as test_client:
        async with AsyncClient(base_url="http://127.0.0.1:8000", headers=test_client.headers) as client:
            response = await client.post(
                "/swagger/api/v1/users/create-user",
                json={
                    "username": test_user_create["username"],
                    "email": test_user_create["email"],
                    "password": test_user_create["password"],
                },
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                },
            )

            assert response.status_code == 201, f"Response text: {response.text}"
            response_data = response.json()
            assert response_data["username"] == test_user_create["username"]
            assert response_data["email"] == test_user_create["email"]


@pytest.mark.asyncio
async def test_login_access_token_success(test_user_create):
    with TestClient(app) as test_client:
        async with AsyncClient(base_url="http://127.0.0.1:8000", headers=test_client.headers) as client:

            await client.post(
                "/swagger/api/v1/users/create-user",
                json={
                    "username": test_user_create["username"],
                    "email": test_user_create["email"],
                    "password": test_user_create["password"],
                },
            )

            response = await client.post(
                "/swagger/api/v1/login/access-token",
                data={
                    "username": test_user_create["email"],
                    "password": test_user_create["password"],
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            assert response.status_code == 200, f"Response text: {response.text}"

            token_data = response.json()
            assert "access_token" in token_data
            assert token_data["access_token"] is not None

@pytest.mark.asyncio
async def test_login_access_token_failure(test_user_create):
    with TestClient(app) as test_client:
        async with AsyncClient(base_url="http://127.0.0.1:8000", headers=test_client.headers) as client:

            response = await client.post(
                "/swagger/api/v1/login/access-token",
                data={
                    "username": test_user_create["email"],
                    "password": "wrongpassword",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            assert response.status_code == 400, f"Response text: {response.text}"
            error_data = response.json()
            assert error_data["detail"] == "Incorrect email or password"



@pytest_asyncio.fixture
async def authenticated_client():
    async with AsyncClient(base_url="http://127.0.0.1:8000") as client:

        login_data = {
            "username": "testuser@example.com",
            "password": "password123",
        }
        response = await client.post("/swagger/api/v1/login/access-token", data=login_data)
        token = response.json().get("access_token")

        if not token:
            raise RuntimeError("Не вдалося отримати токен доступу")

        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


@pytest.mark.asyncio
async def test_create_receipt_success(authenticated_client):

    receipt_input = {
        "products": [
            {"name": "Product 1", "price": 10.5, "quantity": 2},
            {"name": "Product 2", "price": 5.0, "quantity": 1},
        ],
        "payment_type": "cash",
        "payment_amount": 30.0,
    }

    response = await authenticated_client.post("/swagger/api/v1/products/receipts/", json=receipt_input)

    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert "id" in data
    assert data["total"] == 26.0
    assert data["rest"] == 4.0



@pytest.mark.asyncio
async def test_get_receipts_with_pagination(authenticated_client):

    params = {
        "offset": 0,
        "limit": 10,
        "min_total": 20,
    }


    response = await authenticated_client.get("/swagger/api/v1/products/receipts/", params=params)
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert "total_count" in data
    assert isinstance(data["items"], list)
#
#
@pytest.mark.asyncio
async def test_get_public_receipt_text(authenticated_client):
    receipt_id = "5f6e97c6-58db-4c5f-8b42-e5c18bc4f31d"

    response = await authenticated_client.get(f"/swagger/api/v1/products/receipts/{receipt_id}/text?line_width=32")
    assert response.status_code == 200, f"Response: {response.text}"
    lines = response.json()
    assert lines[0].strip() == "ФОП Джонсонюк Борис", f"First line mismatch: {lines[0]}"


@pytest.mark.asyncio
async def test_insufficient_funds(authenticated_client):
    receipt_input = {
        "products": [
            {"name": "Product 1", "price": 50.0, "quantity": 1},
        ],
        "payment_type": "cash",
        "payment_amount": 20.0,
    }

    response = await authenticated_client.post("/swagger/api/v1/products/receipts/", json=receipt_input)
    assert response.status_code == 400, f"Response: {response.text}"
    assert "Insufficient funds" in response.json()["detail"], f"Detail mismatch: {response.json()['detail']}"

#
@pytest.mark.asyncio
async def test_receipt_not_found(authenticated_client):
    invalid_receipt_id = "00000000-0000-0000-0000-000000000000"

    response = await authenticated_client.get(f"/swagger/api/v1/products/receipts/{invalid_receipt_id}/")
    assert response.status_code == 500
    assert response.json()["detail"] == "404: Receipt not found"



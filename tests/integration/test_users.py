from __future__ import annotations

import pytest
import uuid


@pytest.mark.asyncio
async def test_create_and_fetch_user(client):
    unique_email = f"test-{uuid.uuid4()}@example.com"
    payload = {"email": unique_email, "is_active": True}

    create_response = await client.post("/api/users/", json=payload)
    assert create_response.status_code == 201

    data = create_response.json()
    user_id = data["id"]
    assert data["email"] == payload["email"]
    assert data["is_active"] is True

    fetch_response = await client.get(f"/api/users/{user_id}")
    assert fetch_response.status_code == 200

    fetched = fetch_response.json()
    assert fetched["id"] == user_id
    assert fetched["email"] == payload["email"]


@pytest.mark.asyncio
async def test_list_users(client, user_factory):
    await user_factory(email="list@example.com")

    response = await client.get("/api/users/")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["email"] == "list@example.com" for item in payload["items"])


@pytest.mark.asyncio
async def test_update_user(client, user_factory):
    user = await user_factory(email="update@example.com")

    update_response = await client.patch(
        f"/api/users/{user.id}",
        json={"email": "updated@example.com", "is_active": False},
    )
    assert update_response.status_code == 200

    updated = update_response.json()
    assert updated["email"] == "updated@example.com"
    assert updated["is_active"] is False


@pytest.mark.asyncio
async def test_update_requires_payload(client, user_factory):
    user = await user_factory(email="noop@example.com")

    response = await client.patch(f"/api/users/{user.id}", json={})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_user(client, user_factory):
    user = await user_factory(email="delete@example.com")

    response = await client.delete(f"/api/users/{user.id}")
    assert response.status_code == 204

    follow_up = await client.get(f"/api/users/{user.id}")
    assert follow_up.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "is_active": True}
    first = await client.post("/api/users/", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/users/", json=payload)
    assert second.status_code == 409

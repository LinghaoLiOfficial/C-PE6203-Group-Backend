from fastapi.testclient import TestClient


def test_example_item_crud(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/example-items",
        json={"key": "welcome", "title": "Welcome", "description": "Reusable example item"},
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["data"]["id"]

    list_response = client.get("/api/v1/example-items")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["items"][0]["key"] == "welcome"

    detail_response = client.get(f"/api/v1/example-items/{item_id}")
    assert detail_response.status_code == 200

    update_response = client.patch(f"/api/v1/example-items/{item_id}", json={"title": "Updated"})
    assert update_response.status_code == 200
    assert update_response.json()["data"]["title"] == "Updated"

    delete_response = client.delete(f"/api/v1/example-items/{item_id}")
    assert delete_response.status_code == 204

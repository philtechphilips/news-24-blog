from fastapi.testclient import TestClient


def create_category(client: TestClient, headers: dict[str, str], name: str) -> dict:
    response = client.post("/categories/", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_anyone_can_list_categories_sorted_by_name(client, admin_headers):
    create_category(client, admin_headers, "Sports")
    create_category(client, admin_headers, "Art")

    response = client.get("/categories/")

    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["Art", "Sports"]


def test_only_admins_can_write(client, user_headers):
    assert client.post("/categories/", json={"name": "Art"}).status_code == 401
    response = client.post("/categories/", json={"name": "Art"}, headers=user_headers)
    assert response.status_code == 403


def test_duplicate_name_is_rejected(client, admin_headers):
    create_category(client, admin_headers, "Art")
    response = client.post("/categories/", json={"name": "Art"}, headers=admin_headers)
    assert response.status_code == 409


def test_rename_and_delete(client, admin_headers):
    category = create_category(client, admin_headers, "Art")
    create_category(client, admin_headers, "Style")
    url = f"/categories/{category['id']}"

    taken = client.patch(url, json={"name": "Style"}, headers=admin_headers)
    assert taken.status_code == 409

    renamed = client.patch(url, json={"name": "Culture"}, headers=admin_headers)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Culture"

    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.get(url).status_code == 404

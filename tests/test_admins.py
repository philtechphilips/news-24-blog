from tests.conftest import auth_headers, create_user


def me(client, headers) -> dict:
    return client.get("/users/me", headers=headers).json()


def test_create_admin(client, admin_headers):
    payload = {"email": "carol@example.com", "password": "password123"}
    response = client.post("/users/admins", json=payload, headers=admin_headers)

    assert response.status_code == 201
    assert response.json()["role"] == "admin"
    # The new admin can use admin endpoints straight away
    carol = auth_headers(client, "carol@example.com")
    assert client.get("/users/admins", headers=carol).status_code == 200


def test_create_admin_with_taken_email(client, admin_headers):
    payload = {"email": "admin@example.com", "password": "password123"}
    response = client.post("/users/admins", json=payload, headers=admin_headers)
    assert response.status_code == 409


def test_list_admins_only_lists_admins(client, admin_headers):
    create_user(client, "bob@example.com")
    response = client.get("/users/admins", headers=admin_headers)
    assert [u["email"] for u in response.json()] == ["admin@example.com"]


def test_make_and_remove_admin(client, admin_headers):
    bob = create_user(client, "bob@example.com")
    url = f"/users/{bob['id']}/admin"

    made = client.put(url, headers=admin_headers)
    assert made.status_code == 200
    assert made.json()["role"] == "admin"
    assert client.put(url, headers=admin_headers).status_code == 200  # idempotent

    removed = client.delete(url, headers=admin_headers)
    assert removed.status_code == 200
    assert removed.json()["role"] == "user"


def test_admins_cannot_demote_or_delete_themselves(client, admin_headers):
    my_id = me(client, admin_headers)["id"]
    assert (
        client.delete(f"/users/{my_id}/admin", headers=admin_headers).status_code == 400
    )
    assert client.delete(f"/users/{my_id}", headers=admin_headers).status_code == 400


def test_delete_user(client, admin_headers):
    bob = create_user(client, "bob@example.com")
    url = f"/users/{bob['id']}"

    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.get(url, headers=admin_headers).status_code == 404
    assert client.delete(url, headers=admin_headers).status_code == 404


def test_unknown_user_is_404(client, admin_headers):
    url = "/users/00000000-0000-0000-0000-000000000000/admin"
    assert client.put(url, headers=admin_headers).status_code == 404


def test_regular_users_cannot_use_admin_endpoints(client, user_headers):
    bob = create_user(client, "bob@example.com")
    payload = {"email": "eve@example.com", "password": "password123"}
    assert client.get("/users/admins", headers=user_headers).status_code == 403
    assert (
        client.post("/users/admins", json=payload, headers=user_headers).status_code
        == 403
    )
    assert (
        client.put(f"/users/{bob['id']}/admin", headers=user_headers).status_code == 403
    )
    assert client.delete(f"/users/{bob['id']}", headers=user_headers).status_code == 403

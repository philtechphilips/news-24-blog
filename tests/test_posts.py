import uuid

from fastapi.testclient import TestClient

from app.core.slugs import slugify


def create_post(client: TestClient, headers: dict[str, str], **fields) -> dict:
    payload = {"title": "Markets rally again", "body": "Stocks rose."} | fields
    response = client.post("/posts/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_slugify():
    assert slugify("Héllo, World!  2026") == "hello-world-2026"
    assert slugify("???") == "post"


def test_slug_is_generated_and_made_unique(client, admin_headers):
    first = create_post(client, admin_headers)
    second = create_post(client, admin_headers)

    assert first["slug"] == "markets-rally-again"
    assert second["slug"] == "markets-rally-again-2"
    assert first["is_published"] is False


def test_explicit_slug_that_is_taken_returns_409(client, admin_headers):
    create_post(client, admin_headers, slug="rally")
    payload = {"title": "Another", "body": "x", "slug": "rally"}
    response = client.post("/posts/", json=payload, headers=admin_headers)
    assert response.status_code == 409


def test_only_admins_can_write(client, user_headers):
    payload = {"title": "Markets", "body": "x"}
    assert client.post("/posts/", json=payload).status_code == 401
    assert client.post("/posts/", json=payload, headers=user_headers).status_code == 403
    assert client.get("/posts/all", headers=user_headers).status_code == 403


def test_public_endpoints_only_show_published_posts(client, admin_headers):
    create_post(client, admin_headers, title="Draft story")
    published = create_post(
        client, admin_headers, title="Live story", is_published=True
    )

    listed = client.get("/posts/").json()
    assert [p["title"] for p in listed] == ["Live story"]
    assert client.get(f"/posts/slug/{published['slug']}").status_code == 200
    assert client.get("/posts/slug/draft-story").status_code == 404

    everything = client.get("/posts/all", headers=admin_headers).json()
    assert {p["title"] for p in everything} == {"Draft story", "Live story"}


def test_category_filter_and_unknown_category(client, admin_headers):
    category = client.post(
        "/categories/", json={"name": "Economy"}, headers=admin_headers
    ).json()
    create_post(client, admin_headers, category_id=category["id"], is_published=True)
    create_post(client, admin_headers, title="Elsewhere", is_published=True)

    filtered = client.get("/posts/", params={"category_id": category["id"]}).json()
    assert [p["title"] for p in filtered] == ["Markets rally again"]

    payload = {"title": "Lost", "body": "x", "category_id": str(uuid.uuid4())}
    response = client.post("/posts/", json=payload, headers=admin_headers)
    assert response.status_code == 422


def test_update_can_clear_optional_fields(client, admin_headers):
    post = create_post(client, admin_headers, excerpt="Short summary")
    url = f"/posts/{post['id']}"

    response = client.patch(
        url,
        json={"excerpt": None, "title": None, "is_published": True},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["excerpt"] is None
    assert body["title"] == "Markets rally again"  # required fields ignore null
    assert body["is_published"] is True


def test_delete(client, admin_headers):
    post = create_post(client, admin_headers)
    url = f"/posts/{post['id']}"
    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.get(url, headers=admin_headers).status_code == 404


def test_search(client, admin_headers):
    economy = client.post(
        "/categories/", json={"name": "Economy"}, headers=admin_headers
    ).json()
    create_post(
        client,
        admin_headers,
        title="Central banks hold rates",
        body="Inflation is cooling.",
        category_id=economy["id"],
        is_published=True,
    )
    create_post(
        client,
        admin_headers,
        title="Cup final preview",
        body="Why the banks of the river flood every spring.",
        is_published=True,
    )
    create_post(client, admin_headers, title="Banks draft", body="x")  # unpublished

    def search(q: str) -> list[str]:
        return [p["title"] for p in client.get("/posts/", params={"q": q}).json()]

    # Title matches come first; drafts never show up
    assert search("BANKS") == ["Central banks hold rates", "Cup final preview"]
    assert search("inflation") == ["Central banks hold rates"]  # body
    assert search("economy") == ["Central banks hold rates"]  # category name
    assert search("banks river") == ["Cup final preview"]  # every word must match
    assert search("100%") == []  # % is literal, not a wildcard
    assert len(search("   ")) == 2  # blank search lists everything


def test_search_query_too_long(client):
    assert client.get("/posts/", params={"q": "x" * 101}).status_code == 422


def test_pagination_with_total_count(client, admin_headers):
    for i in range(14):
        create_post(
            client, admin_headers, title=f"Story number {i:02d}", is_published=True
        )
    create_post(client, admin_headers, title="Unpublished story")

    first = client.get("/posts/", params={"limit": 12})
    second = client.get("/posts/", params={"limit": 12, "skip": 12})

    assert first.headers["x-total-count"] == "14"  # drafts don't count
    assert len(first.json()) == 12
    assert len(second.json()) == 2
    titles = {p["title"] for p in first.json() + second.json()}
    assert len(titles) == 14  # no post on two pages

    # The count follows the filters, e.g. a search
    searched = client.get("/posts/", params={"q": "number 1", "limit": 1})
    assert searched.headers["x-total-count"] == "5"  # 01, 10, 11, 12, 13

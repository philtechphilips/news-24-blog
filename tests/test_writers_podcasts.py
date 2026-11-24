import uuid

from fastapi.testclient import TestClient


def create(client: TestClient, headers, path: str, **fields) -> dict:
    response = client.post(path, json=fields, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def writer(client, headers, name="Kristin Watson", **fields) -> dict:
    return create(
        client, headers, "/writers/", name=name, role="Senior Writer", **fields
    )


# ---------- Writers ----------


def test_writers_are_public_and_listed_oldest_first(client, admin_headers):
    writer(client, admin_headers, "Kristin Watson")
    writer(client, admin_headers, "Marvin Roy")

    listed = client.get("/writers/").json()
    assert [w["name"] for w in listed] == ["Kristin Watson", "Marvin Roy"]
    assert client.get("/writers/slug/marvin-roy").json()["name"] == "Marvin Roy"


def test_writer_slug_generated_and_unique(client, admin_headers):
    first = writer(client, admin_headers, "Kristin Watson")
    second = writer(client, admin_headers, "Kristin Watson")
    assert (first["slug"], second["slug"]) == ("kristin-watson", "kristin-watson-2")

    payload = {"name": "Other", "role": "Editor", "slug": "kristin-watson"}
    response = client.post("/writers/", json=payload, headers=admin_headers)
    assert response.status_code == 409


def test_only_admins_can_write_writers(client, user_headers):
    payload = {"name": "Kristin Watson", "role": "Senior Writer"}
    assert client.post("/writers/", json=payload).status_code == 401
    assert (
        client.post("/writers/", json=payload, headers=user_headers).status_code == 403
    )


def test_update_and_delete_writer(client, admin_headers):
    w = writer(client, admin_headers, location="Lagos", social={"x": "https://x.com/k"})
    url = f"/writers/{w['id']}"

    updated = client.patch(
        url, json={"location": None, "role": "Editor"}, headers=admin_headers
    )
    assert updated.json()["location"] is None
    assert updated.json()["role"] == "Editor"

    bad_social = client.patch(
        url, json={"social": {"myspace": "x"}}, headers=admin_headers
    )
    assert bad_social.status_code == 422

    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.get(url).status_code == 404


# ---------- Podcasts ----------


def podcast(client, headers, **fields) -> dict:
    payload = {"title": "SEO Mastery", "description": "Rank higher."} | fields
    return create(client, headers, "/podcasts/", **payload)


def test_public_podcasts_are_published_only(client, admin_headers):
    podcast(client, admin_headers, title="Draft episode")
    live = podcast(client, admin_headers, title="Live episode", is_published=True)

    assert [p["title"] for p in client.get("/podcasts/").json()] == ["Live episode"]
    assert client.get(f"/podcasts/slug/{live['slug']}").status_code == 200
    assert client.get("/podcasts/slug/draft-episode").status_code == 404
    everything = client.get("/podcasts/all", headers=admin_headers).json()
    assert len(everything) == 2


def test_podcast_host_must_exist(client, admin_headers):
    host = writer(client, admin_headers)
    ep = podcast(client, admin_headers, host_id=host["id"], duration_minutes=45)
    assert ep["host_id"] == host["id"]

    payload = {"title": "Lost", "description": "x", "host_id": str(uuid.uuid4())}
    response = client.post("/podcasts/", json=payload, headers=admin_headers)
    assert response.status_code == 422


def test_only_admins_can_write_podcasts(client, user_headers):
    payload = {"title": "SEO Mastery", "description": "Rank higher."}
    assert client.post("/podcasts/", json=payload).status_code == 401
    assert (
        client.post("/podcasts/", json=payload, headers=user_headers).status_code == 403
    )
    assert client.get("/podcasts/all", headers=user_headers).status_code == 403


def test_update_and_delete_podcast(client, admin_headers):
    ep = podcast(client, admin_headers, audio_url="https://cdn.example.com/ep.mp3")
    url = f"/podcasts/{ep['id']}"

    updated = client.patch(
        url,
        json={"audio_url": None, "title": None, "is_published": True},
        headers=admin_headers,
    )
    assert updated.json()["audio_url"] is None
    assert updated.json()["title"] == "SEO Mastery"  # required fields ignore null
    assert updated.json()["is_published"] is True

    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.get(url, headers=admin_headers).status_code == 404


# ---------- Post authors ----------


def test_posts_by_writer(client, admin_headers):
    kristin = writer(client, admin_headers, "Kristin Watson")
    marvin = writer(client, admin_headers, "Marvin Roy")
    for title, author in (("By Kristin", kristin), ("By Marvin", marvin)):
        payload = {
            "title": title,
            "body": "x",
            "is_published": True,
            "writer_id": author["id"],
        }
        assert (
            client.post("/posts/", json=payload, headers=admin_headers).status_code
            == 201
        )

    mine = client.get("/posts/", params={"writer_id": kristin["id"]}).json()
    assert [p["title"] for p in mine] == ["By Kristin"]

    payload = {"title": "Ghost", "body": "x", "writer_id": str(uuid.uuid4())}
    assert (
        client.post("/posts/", json=payload, headers=admin_headers).status_code == 422
    )

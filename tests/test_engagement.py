import asyncio
import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.engagement import live
from app.engagement.live import LiveHub
from app.posts.models import Posts
from tests.conftest import auth_headers


@pytest.fixture
def post(db: Session) -> Posts:
    post = Posts(title="Live post", slug="live-post", body="Body", is_published=True)
    db.add(post)
    db.commit()
    return post


@pytest.fixture
def events(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict]]:
    """Everything the routes publish to live readers, in order."""
    published: list[tuple[str, dict]] = []

    def record(_post_id, event: str, data: dict) -> None:
        published.append((event, data))

    monkeypatch.setattr(live.hub, "publish", record)
    return published


def sign_up(client: TestClient, email: str, name: str | None = None) -> dict[str, str]:
    body = {"email": email, "password": "password123"}
    if name:
        body["name"] = name
    assert client.post("/users/", json=body).status_code == 201
    return auth_headers(client, email)


def engagement(client: TestClient, post: Posts, headers=None) -> dict:
    response = client.get(f"/posts/{post.id}/engagement", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def comment(client, post, headers, body="Nice one", parent_id=None) -> dict:
    response = client.post(
        f"/posts/{post.id}/comments",
        json={"body": body, "parent_id": parent_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_guests_see_empty_engagement(client: TestClient, post: Posts):
    assert engagement(client, post) == {
        "stats": {"likes": 0, "comments": 0, "shares": 0},
        "comments": [],
        "liked": False,
        "liked_comments": [],
    }


def test_commenting_needs_login(client: TestClient, post: Posts):
    response = client.post(f"/posts/{post.id}/comments", json={"body": "Hi"})
    assert response.status_code == 401


def test_comments_and_replies_are_listed_and_published(
    client: TestClient, post: Posts, events
):
    ada = sign_up(client, "ada@example.com", "Ada")
    bo = sign_up(client, "bo@example.com")
    first = comment(client, post, ada, "  First!  ")
    reply = comment(client, post, bo, "Welcome", parent_id=first["id"])

    assert first["body"] == "First!"
    assert first["author"]["name"] == "Ada"
    assert reply["author"]["name"] == "Reader"  # no display name set
    data = engagement(client, post)
    assert [c["id"] for c in data["comments"]] == [first["id"], reply["id"]]
    assert data["comments"][1]["parent_id"] == first["id"]
    assert data["stats"]["comments"] == 2

    assert [e for e, _ in events] == ["comment", "stats", "comment", "stats"]
    assert events[0][1]["id"] == first["id"]
    assert events[-1][1] == {"likes": 0, "comments": 2, "shares": 0}


def test_bad_comments_are_rejected(client: TestClient, post: Posts, db: Session):
    ada = sign_up(client, "ada@example.com")
    url = f"/posts/{post.id}/comments"
    assert client.post(url, json={"body": "   "}, headers=ada).status_code == 422
    assert client.post(url, json={"body": "x" * 2001}, headers=ada).status_code == 422

    other = Posts(title="Other", slug="other", body="Body", is_published=True)
    db.add(other)
    db.commit()
    elsewhere = comment(client, other, ada)
    response = client.post(
        url, json={"body": "Hi", "parent_id": elsewhere["id"]}, headers=ada
    )
    assert response.status_code == 422


def test_unpublished_posts_have_no_engagement(client: TestClient, db: Session):
    draft = Posts(title="Draft", slug="draft", body="Body", is_published=False)
    db.add(draft)
    db.commit()
    ada = sign_up(client, "ada@example.com")
    assert client.get(f"/posts/{draft.id}/engagement").status_code == 404
    assert client.get(f"/posts/{draft.id}/live").status_code == 404
    assert client.put(f"/posts/{draft.id}/like", headers=ada).status_code == 404
    assert client.post(f"/posts/{draft.id}/share").status_code == 404


def test_liking_a_post(client: TestClient, post: Posts, events):
    ada = sign_up(client, "ada@example.com")
    bo = sign_up(client, "bo@example.com")
    url = f"/posts/{post.id}/like"

    assert client.put(url).status_code == 401
    assert client.put(url, headers=ada).json() == {"liked": True, "likes": 1}
    assert client.put(url, headers=ada).json() == {"liked": True, "likes": 1}
    assert client.put(url, headers=bo).json() == {"liked": True, "likes": 2}
    assert engagement(client, post, ada)["liked"] is True
    assert engagement(client, post)["liked"] is False

    assert client.delete(url, headers=ada).json() == {"liked": False, "likes": 1}
    assert engagement(client, post, ada)["liked"] is False
    assert events[-2][0] == "post_like"
    assert events[-2][1]["liked"] is False
    assert events[-1] == ("stats", {"likes": 1, "comments": 0, "shares": 0})


def test_liking_a_comment(client: TestClient, post: Posts, events):
    ada = sign_up(client, "ada@example.com")
    first = comment(client, post, ada)
    url = f"/comments/{first['id']}/like"

    assert client.put(url, headers=ada).json() == {"liked": True, "likes": 1}
    data = engagement(client, post, ada)
    assert data["comments"][0]["likes"] == 1
    assert data["liked_comments"] == [first["id"]]
    assert events[-1][0] == "comment_like"
    assert events[-1][1]["comment_id"] == first["id"]
    assert events[-1][1]["likes"] == 1

    assert client.delete(url, headers=ada).json() == {"liked": False, "likes": 0}
    assert engagement(client, post, ada)["liked_comments"] == []


def test_deleting_a_comment_removes_its_replies(
    client: TestClient, post: Posts, events, admin_headers
):
    ada = sign_up(client, "ada@example.com")
    bo = sign_up(client, "bo@example.com")
    first = comment(client, post, ada)
    reply = comment(client, post, bo, parent_id=first["id"])
    nested = comment(client, post, ada, parent_id=reply["id"])
    keep = comment(client, post, bo)

    assert client.delete(f"/comments/{first['id']}", headers=bo).status_code == 403
    assert client.delete(f"/comments/{first['id']}", headers=ada).status_code == 204

    assert [c["id"] for c in engagement(client, post)["comments"]] == [keep["id"]]
    removed = next(data for event, data in events if event == "comment_removed")
    assert set(removed["ids"]) == {first["id"], reply["id"], nested["id"]}
    assert events[-1] == ("stats", {"likes": 0, "comments": 1, "shares": 0})

    # Admins can remove anyone's comment.
    url = f"/comments/{keep['id']}"
    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.delete(url, headers=ada).status_code == 404


def test_anyone_can_share(client: TestClient, post: Posts, events):
    url = f"/posts/{post.id}/share"
    assert client.post(url).json()["shares"] == 1
    assert client.post(url).json()["shares"] == 2
    assert engagement(client, post)["stats"]["shares"] == 2
    assert events[-1] == ("stats", {"likes": 0, "comments": 0, "shares": 2})


def test_readers_can_set_their_display_name(client: TestClient, post: Posts):
    ada = sign_up(client, "ada@example.com")
    comment(client, post, ada)
    response = client.patch("/users/me", json={"name": "  Ada L  "}, headers=ada)
    assert response.json()["name"] == "Ada L"
    assert engagement(client, post)["comments"][0]["author"]["name"] == "Ada L"
    assert client.patch("/users/me", json={"name": ""}, headers=ada).status_code == 422


# ---------- The live hub ----------


def test_hub_delivers_events_published_from_other_threads():
    hub = LiveHub()
    post_id = uuid.uuid4()

    async def main():
        async with hub.subscribe(post_id) as queue:
            assert hub.subscriber_count(post_id) == 1
            # Sync routes publish from FastAPI's worker threads.
            thread = threading.Thread(
                target=hub.publish, args=(post_id, "stats", {"likes": 1})
            )
            thread.start()
            thread.join()
            assert await asyncio.wait_for(queue.get(), 1) == ("stats", {"likes": 1})
        assert hub.subscriber_count(post_id) == 0

    asyncio.run(main())


def test_hub_tells_slow_readers_to_reload(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(live, "QUEUE_SIZE", 2)
    hub = LiveHub()
    post_id = uuid.uuid4()

    async def main():
        async with hub.subscribe(post_id) as queue:
            for n in range(3):
                hub.publish(post_id, "stats", {"n": n})
            await asyncio.sleep(0)  # let the queued callbacks run
            assert queue.get_nowait() == live.READY
            assert queue.empty()

    asyncio.run(main())

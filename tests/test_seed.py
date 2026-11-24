from app.podcasts.models import Podcasts
from app.posts.models import Posts
from app.seed import load_seed_data, seed
from app.writers.models import Writers


def test_seed_loads_everything_once(db):
    data = load_seed_data()

    assert seed(db, data) == {
        "writers": len(data["writers"]),
        "categories": len(data["categories"]),
        "posts": len(data["posts"]),
        "podcasts": len(data["podcasts"]),
    }
    # Running it again adds nothing
    assert set(seed(db, data).values()) == {0}

    post = db.query(Posts).filter_by(slug=data["posts"][0]["slug"]).one()
    assert post.is_published and post.category_id and post.writer_id
    podcast = db.query(Podcasts).filter_by(slug=data["podcasts"][0]["slug"]).one()
    assert db.get(Writers, podcast.host_id).slug == data["podcasts"][0]["host"]


def test_seed_fills_in_missing_authors(db):
    data = load_seed_data()
    seed(db, data)
    post = db.query(Posts).first()
    post.writer_id = None
    db.commit()

    seed(db, data)
    db.refresh(post)
    assert post.writer_id is not None

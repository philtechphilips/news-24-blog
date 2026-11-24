import json

from app.posts.models import Posts
from app.seed import SEED_FILE, seed


def test_seed_loads_everything_once(db):
    data = json.loads(SEED_FILE.read_text())

    assert seed(db, data) == (len(data["categories"]), len(data["posts"]))
    # Running it again adds nothing
    assert seed(db, data) == (0, 0)

    post = db.query(Posts).filter_by(slug=data["posts"][0]["slug"]).one()
    assert post.is_published
    assert post.category_id is not None

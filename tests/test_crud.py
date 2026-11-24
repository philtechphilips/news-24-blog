"""The reusable crud helpers: filters, where, order_by and join together."""

from app.categories.models import Categories
from app.core import crud
from app.posts.models import Posts


def add_post(db, title: str, category: Categories | None = None, published=True):
    post = Posts(
        title=title,
        slug=title.lower().replace(" ", "-"),
        body="x",
        tags=[],
        is_published=published,
        category_id=category.id if category else None,
    )
    db.add(post)
    db.commit()
    return post


def test_where_and_order_by(db):
    for title in ("Banana", "apple", "Cherry"):
        add_post(db, title)
    add_post(db, "Avocado", published=False)

    rows = crud.fetch(
        db,
        Posts,
        {"is_published": True},
        where=[Posts.title.ilike("%a%")],
        order_by=[Posts.title.asc()],
    )
    assert [p.title for p in rows] == ["Banana", "apple"]  # plain string order
    assert (
        crud.count_items(
            db, Posts, {"is_published": True}, where=[Posts.title.ilike("%a%")]
        )
        == 2
    )
    assert crud.fetch_one(db, Posts, where=[Posts.title == "Cherry"]).title == "Cherry"


def test_join(db):
    art = Categories(name="Art")
    sport = Categories(name="Sport")
    db.add_all([art, sport])
    db.commit()
    add_post(db, "Gallery opening", art)
    add_post(db, "Cup final", sport)
    add_post(db, "No category")

    on_category = [(Categories, Posts.category_id == Categories.id)]
    rows = crud.fetch(
        db,
        Posts,
        join=on_category,
        where=[Categories.name.in_(["Art", "Sport"])],
        order_by=[Categories.name.desc()],
    )
    assert [p.title for p in rows] == ["Cup final", "Gallery opening"]
    assert (
        crud.count_items(db, Posts, join=on_category, where=[Categories.name == "Art"])
        == 1
    )
    # Outer join: posts without a category are still there when not filtered out
    assert len(crud.simple_list(db, Posts, join=on_category)) == 3

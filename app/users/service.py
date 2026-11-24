import uuid

from sqlalchemy.orm import Session

from app.core import crud
from app.core.security import hash_password
from app.users.models import Role, User
from app.users.schemas import UserCreate


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    return crud.fetch_one(db, User, {"id": user_id})


def get_user_by_email(db: Session, email: str) -> User | None:
    return crud.fetch_one(db, User, {"email": email})


def list_users(
    db: Session, limit: int = 10, skip: int = 0, role: Role | None = None
) -> list[User]:
    filters = {"role": role} if role else None
    return crud.fetch(db, User, filters, limit=limit, skip=skip)


def create_user(db: Session, user_in: UserCreate, role: Role = Role.USER) -> User:
    data = {
        "email": user_in.email,
        "password": hash_password(user_in.password),
        "role": role,
    }
    return crud.create(db, User, data)


def set_role(db: Session, user: User, role: Role) -> User:
    return crud.update(db, User, {"id": user.id}, {"role": role})


def delete_user(db: Session, user: User) -> None:
    # Their password reset tokens go too (ON DELETE CASCADE).
    crud.hard_delete(db, User, {"id": user.id})

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.security import create_access_token, hash_password, optional_auth, verify_password
from app.database.session import SessionLocal
from app.models.entities import User
from app.schemas.entities import TokenOut
from app.schemas.requests import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

DEMO_USERS = {
    "admin": ("ADMIN", "UrbanRelay Administrator"),
    "operator": ("MUNICIPAL_OPERATOR", "Municipal Operations Officer"),
    "dispatcher": ("DISPATCHER", "Logistics Dispatcher"),
    "hubowner": ("HUB_OPERATOR", "Kirana Hub Owner"),
    "courier": ("COURIER", "Last-mile Courier"),
}


@router.post("/login", response_model=TokenOut)
def login(req: LoginRequest) -> TokenOut:
    db = SessionLocal()
    try:
        if req.demo:
            username = "admin"
        elif req.username and req.password:
            username = req.username
        else:
            raise HTTPException(status_code=422, detail="Provide credentials or demo=true")

        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found — run scripts/seed_demo.py first")
        if not req.demo and not verify_password(req.password or "", user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        token = create_access_token(user.id, user.role, user.username)
        return TokenOut(access_token=token, role=user.role, username=user.username, full_name=user.full_name)
    finally:
        db.close()


@router.get("/me")
def me(claims: dict | None = Depends(optional_auth)) -> dict:
    if claims is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"sub": claims["sub"], "role": claims["role"], "username": claims["username"]}


def seed_users(db) -> None:
    if db.execute(select(User).limit(1)).first():
        return
    for username, (role, full_name) in DEMO_USERS.items():
        db.add(
            User(
                username=username,
                password_hash=hash_password("demo1234"),
                role=role,
                full_name=full_name,
            )
        )
    db.commit()
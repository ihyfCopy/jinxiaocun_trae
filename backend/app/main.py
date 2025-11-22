from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import User, Product, Customer
from .auth import router as auth_router, get_password_hash
from .routers import products as products_router
from .routers import customers as customers_router
from .routers import orders as orders_router


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="进销存系统 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    try:
        # seed admin user
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", password_hash=get_password_hash("admin"), display_name="管理员"))
        # seed some products
        if db.query(Product).count() == 0:
            db.add_all([
                Product(name="苹果", sku="APL-001", price=5.5, stock=100, description="新鲜苹果"),
                Product(name="香蕉", sku="BAN-001", price=4.2, stock=80, description="进口香蕉"),
                Product(name="牛奶", sku="MLK-001", price=6.8, stock=60, description="纯牛奶"),
            ])
        # seed a customer
        if db.query(Customer).count() == 0:
            db.add(Customer(name="张三", phone="13800000000", address="北京市海淀区"))
        db.commit()
    finally:
        db.close()


app.include_router(auth_router)
app.include_router(products_router.router)
app.include_router(customers_router.router)
app.include_router(orders_router.router)


@app.get("/", tags=["健康检查"])
def root():
    return {"message": "进销存系统后端运行正常"}

# 前端静态页面挂载
WEB_DIR = str((Path(__file__).resolve().parents[2] / "web").resolve())
app.mount("/ui", StaticFiles(directory=WEB_DIR, html=True), name="ui")

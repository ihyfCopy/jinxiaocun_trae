from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Product
from ..schemas import ProductCreate, ProductUpdate, ProductOut, ProductPage
from ..auth import get_current_user


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/products", tags=["商品"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[ProductOut])
def list_products(
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Product).order_by(Product.id.desc())
    if page and page_size:
        return q.offset((page - 1) * page_size).limit(page_size).all()
    return q.all()


@router.post("/", response_model=ProductOut)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    if payload.sku and payload.sku != "无":
        exist = db.query(Product).filter(Product.sku == payload.sku).first()
        if exist:
            raise HTTPException(status_code=400, detail="SKU已存在")

    product = Product(**payload.model_dump())
    if not product.sku:
        product.sku = "无"
    if not product.original_weight:
        product.original_weight = "无"

    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    if payload.sku and payload.sku != "无" and payload.sku != product.sku:
        exist = db.query(Product).filter(Product.sku == payload.sku).first()
        if exist:
            raise HTTPException(status_code=400, detail="SKU已存在")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(product, k, v)

    if not product.sku:
        product.sku = "无"
    if not product.original_weight:
        product.original_weight = "无"

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    db.delete(product)
    db.commit()
    return {"message": "已删除"}
@router.get("/page", response_model=ProductPage)
def list_products_paged(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Product).order_by(Product.id.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}

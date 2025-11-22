from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Order, OrderItem, Product, Customer
from ..schemas import OrderCreate, OrderOut, OrderPage
from ..auth import get_current_user


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/orders", tags=["订单"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[OrderOut])
def list_orders(
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Order).order_by(Order.id.desc())
    if page and page_size:
        return q.offset((page - 1) * page_size).limit(page_size).all()
    return q.all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.post("/", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="订单至少包含一个商品")

    order = Order(
        customer_id=payload.customer_id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_address=payload.customer_address,
    )

    total = 0.0
    for item in payload.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"商品不存在: {item.product_id}")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"库存不足: {product.name}")
        subtotal = product.price * item.quantity
        total += subtotal
        unit = getattr(item, "unit", None) or "件"
        if unit not in ("件", "斤"):
            raise HTTPException(status_code=400, detail=f"单位不合法: {unit}")
        order.items.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            unit_price=product.price,
            quantity=item.quantity,
            unit=unit,
            subtotal=subtotal,
        ))
        product.stock -= item.quantity

    # if selecting an existing customer, copy info
    if payload.customer_id:
        customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
        if customer:
            order.customer = customer
            if not order.customer_name:
                order.customer_name = customer.name
            if not order.customer_phone:
                order.customer_phone = customer.phone
            if not order.customer_address:
                order.customer_address = customer.address

    order.total_amount = total
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
@router.get("/page", response_model=OrderPage)
def list_orders_paged(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Order).order_by(Order.id.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}

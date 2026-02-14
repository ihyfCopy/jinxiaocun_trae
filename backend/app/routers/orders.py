from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Order, OrderItem, Product, Customer
from ..schemas import OrderCreate, OrderOut, OrderPage, OrderItemCreate
from ..auth import get_current_user


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/orders", tags=["订单"], dependencies=[Depends(get_current_user)])


@router.get("/page", response_model=OrderPage)
def list_orders_paged(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Order).order_by(Order.id.desc())
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(func.coalesce(Order.customer_name, "").like(like))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/", response_model=list[OrderOut])
def list_orders(
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Order).order_by(Order.id.desc())
    if q:
        like = f"%{q}%"
        query = query.filter(
            (func.coalesce(Order.customer_name, "").like(like)) |
            (func.strftime('%Y-%m-%d %H:%M:%S', Order.created_at).like(like))
        )
    if page and page_size:
        return query.offset((page - 1) * page_size).limit(page_size).all()
    return query.all()


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
        status="未付款",
    )

    total = 0.0
    for item in payload.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"商品不存在: {item.product_id}")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"库存不足: {product.name}")
        price = getattr(item, "unit_price", None)
        if price is None:
            price = product.price
        if price < 0:
            raise HTTPException(status_code=400, detail=f"单价不合法: {price}")
        subtotal = price * item.quantity
        total += subtotal
        unit = getattr(item, "unit", None) or "件"
        if unit not in ("件", "斤"):
            raise HTTPException(status_code=400, detail=f"单位不合法: {unit}")
        order.items.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            unit_price=price,
            quantity=item.quantity,
            unit=unit,
            subtotal=subtotal,
        ))
        if unit != '斤':
            product.stock -= item.quantity

    # if selecting an existing customer, copy info; else create temp customer
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
    else:
        name = payload.customer_name or "散客"
        phone = payload.customer_phone or None
        address = payload.customer_address or None
        temp_cust = Customer(name=name, phone=phone, address=address)
        db.add(temp_cust)
        db.flush()
        order.customer = temp_cust
        order.customer_id = temp_cust.id
        order.customer_name = temp_cust.name
        order.customer_phone = temp_cust.phone
        order.customer_address = temp_cust.address

    order.total_amount = total
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/pay", response_model=OrderOut)
def toggle_order_status(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if order.status == "已付款":
        order.status = "未付款"
    else:
        order.status = "已付款"
        
    db.commit()
    db.refresh(order)
    return order


@router.put("/{order_id}", response_model=OrderOut)
def update_order(order_id: int, payload: OrderCreate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 1. Restore stock for existing items
    for item in order.items:
        if item.unit != '斤':
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
    
    # 2. Clear existing items
    # Using cascade="all, delete-orphan" in model, so removing from list should work, 
    # but explicit delete is safer to ensure stock logic was handled first (above).
    # Actually, we just restored stock. Now we can clear the list.
    order.items.clear()
    
    # 3. Update customer info
    if payload.customer_id:
        customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
        if customer:
            order.customer = customer
            order.customer_id = customer.id
            order.customer_name = customer.name
            order.customer_phone = customer.phone
            order.customer_address = customer.address
    else:
        order.customer_id = None
        order.customer_name = payload.customer_name
        order.customer_phone = payload.customer_phone
        order.customer_address = payload.customer_address
        
    # 4. Add new items
    total = 0.0
    for item in payload.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"商品不存在: {item.product_id}")
        
        # Check stock (now that we restored old stock, we are checking against available)
        # Note: if product was in old order, its stock is back.
        if item.unit != '斤' and product.stock < item.quantity:
             # Rollback? The stock restoration is already done in memory but not committed? 
             # No, we haven't committed yet. So product.stock in DB + restored amount?
             # Wait, `product` object is from session. 
             # If I updated `product.stock` in step 1, the session has the new value.
             pass
        
        if item.unit != '斤':
            if product.stock < item.quantity:
                 raise HTTPException(status_code=400, detail=f"库存不足: {product.name} (剩余 {product.stock})")
            product.stock -= item.quantity
            
        price = getattr(item, "unit_price", None)
        if price is None:
            price = product.price
        if price < 0:
            raise HTTPException(status_code=400, detail=f"单价不合法: {price}")
            
        subtotal = price * item.quantity
        total += subtotal
        unit = getattr(item, "unit", None) or "件"
        if unit not in ("件", "斤"):
            raise HTTPException(status_code=400, detail=f"单位不合法: {unit}")
            
        order.items.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            unit_price=price,
            quantity=item.quantity,
            unit=unit,
            subtotal=subtotal,
        ))
        
    order.total_amount = total
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/items", response_model=OrderOut)
def add_order_item(order_id: int, payload: OrderItemCreate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    if product.stock < payload.quantity:
        raise HTTPException(status_code=400, detail="库存不足")
    unit = payload.unit or "件"
    if unit not in ("件", "斤"):
        raise HTTPException(status_code=400, detail="单位不合法")
    price = payload.unit_price if payload.unit_price is not None else product.price
    if price < 0:
        raise HTTPException(status_code=400, detail="单价不合法")
    subtotal = price * payload.quantity
    item = OrderItem(
        product_id=product.id,
        product_name=product.name,
        unit_price=price,
        quantity=payload.quantity,
        unit=unit,
        subtotal=subtotal,
    )
    order.items.append(item)
    if unit != '斤':
        product.stock -= payload.quantity
    order.total_amount = sum(i.subtotal for i in order.items)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}/items/{item_id}", response_model=OrderOut)
def delete_order_item(order_id: int, item_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    item = db.query(OrderItem).filter(OrderItem.id == item_id, OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="订单项不存在")
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if product and item.unit != '斤':
        product.stock += item.quantity
    db.delete(item)
    db.commit()
    db.refresh(order)
    order.total_amount = sum(i.subtotal for i in order.items)
    db.commit()
    db.refresh(order)
    return order

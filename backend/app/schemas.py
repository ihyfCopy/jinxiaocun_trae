from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    username: str
    display_name: str


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str


class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    sku: Optional[str] = None
    price: float
    stock: int
    description: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    description: Optional[str] = None


class ProductOut(ProductBase):
    id: int

    class Config:
        from_attributes = True


class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerOut(CustomerBase):
    id: int

    class Config:
        from_attributes = True


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    unit: str | None = None


class OrderCreate(BaseModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    items: List[OrderItemCreate]


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    unit_price: float
    quantity: int
    unit: str | None = None
    subtotal: float

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    created_at: datetime
    total_amount: float
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    items: List[OrderItemOut]

    class Config:
        from_attributes = True


class ProductPage(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    page_size: int


class CustomerPage(BaseModel):
    items: List[CustomerOut]
    total: int
    page: int
    page_size: int


class OrderPage(BaseModel):
    items: List[OrderOut]
    total: int
    page: int
    page_size: int

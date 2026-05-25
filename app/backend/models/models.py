import enum

from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Enum, Float,
                        ForeignKey, Integer, String, UniqueConstraint, func)
from sqlalchemy.orm import relationship

from database.database import base


class Timestampmixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"
    VENDOR = "vendor"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELED = "canceled"


class PaymentStatus(str, enum.Enum):
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"


class ProductAttributeType(str, enum.Enum):
    SIZE = "size"
    COLOR = "color"


class Users(base, Timestampmixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    user_name = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    contact = Column(String)
    hash_password = Column(String, nullable=False)
    DOB = Column(Date)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)

    addresses = relationship("Addresses", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)
    orders = relationship("Orders", back_populates="user")
    reviews = relationship("Reviews", back_populates="user")
    orderItems = relationship("Order_Items", back_populates="user")

class Addresses(base, Timestampmixin):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    address_line_1 = Column(String)
    address_line_2 = Column(String)
    district = Column(String)
    street = Column(String)
    city = Column(String)
    landmark = Column(String)
    state = Column(String)
    country = Column(String)
    postal_code = Column(String)

    user = relationship("Users", back_populates="addresses")
    orders = relationship("Orders", back_populates="shipping_address")


class Categories(base, Timestampmixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)

    subCategory = relationship("Sub_Categories", back_populates="category")
    products = relationship("Products", back_populates="category")


class Sub_Categories(base, Timestampmixin):
    __tablename__ = "sub_categories"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String, nullable=False)
    description = Column(String)

    category = relationship("Categories", back_populates="subCategory")
    product = relationship("Products", back_populates="subCategory")


class Products(base, Timestampmixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    hero_path = Column(JSON)
    cover_img_path = Column(String)
    summary = Column(String)
    description = Column(String)
    sub_category_id = Column(Integer, ForeignKey("sub_categories.id"))

    category = relationship("Categories", back_populates="products")
    subCategory = relationship("Sub_Categories", back_populates="product")
    cartItem = relationship("Cart_Item", back_populates="product")
    productAttribute = relationship(
        "Product_Attribute",
        back_populates="product")
    stock = relationship("Product_Stock", back_populates="product")
    orderItems = relationship("Order_Items", back_populates="product")
    reviews = relationship("Reviews", back_populates="product")


class Product_Attribute(base, Timestampmixin):
    __tablename__ = "product_attribute"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    type = Column(Enum(ProductAttributeType))
    value = Column(String)

    product = relationship("Products", back_populates="productAttribute")


class Product_Stock(base, Timestampmixin):
    __tablename__ = "product_stock"

    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(String, unique=True, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))

    product = relationship("Products", back_populates="stock")
    cartItem = relationship("Cart_Item", back_populates="productStock")
    orderItems = relationship("Order_Items", back_populates="productStock")



class Cart(base, Timestampmixin):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    total = Column(Float, default=0)

    user = relationship("Users", back_populates="cart")
    cartItem = relationship("Cart_Item", back_populates="cart")


class Cart_Item(base, Timestampmixin):
    __tablename__ = "cart_item"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("cart.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    product_stock_id = Column(Integer, ForeignKey("product_stock.id"))
    quantity = Column(Integer, nullable=False)

    cart = relationship("Cart", back_populates="cartItem")
    product = relationship("Products", back_populates="cartItem")
    productStock = relationship("Product_Stock", back_populates="cartItem")


class Orders(base, Timestampmixin):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_number = Column(String, unique=True, nullable=False, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    reason=Column(String,nullable=True)
    total_amount = Column(Float, nullable=False)
    shipping_charge = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    final_amount = Column(Float, nullable=False)
    shipping_address_id = Column(Integer, ForeignKey("addresses.id"))
    tracking_number = Column(String, nullable=True)

    user = relationship("Users", back_populates="orders")
    shipping_address = relationship("Addresses", back_populates="orders")
    orderItems = relationship("Order_Items", back_populates="order")
    payment = relationship("Payments", back_populates="order", uselist=False)


class Order_Items(base, Timestampmixin):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id=Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_stock_id = Column(Integer, ForeignKey("product_stock.id"))
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    user=relationship("Users", back_populates="orderItems")
    order = relationship("Orders", back_populates="orderItems")
    product = relationship("Products", back_populates="orderItems")
    productStock = relationship("Product_Stock", back_populates="orderItems")


class Payments(base, Timestampmixin):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    payment_id = Column(String, unique=True)
    transaction_id = Column(String)
    payment_gateway = Column(String)
    payment_method = Column(String)
    amount = Column(Float, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.INITIATED)

    order = relationship("Orders", back_populates="payment")


class Reviews(base, Timestampmixin):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String)

    user = relationship("Users", back_populates="reviews")
    product = relationship("Products", back_populates="reviews")

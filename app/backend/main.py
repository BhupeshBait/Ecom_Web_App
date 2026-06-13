import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from fastapi.staticfiles import StaticFiles
from database.database import engine
from models import models
from api.cart import router as cart_router
from api.auth import router as auth_router
from api.users import router as users_router
from api.categories import router as category_router
from api.addresses import router as addresses_router
from api.stock import router as stock_router
from api.products import router as products_router
from api.orders import router as orders_router
from api.admin import router as admin_router
from api.reviews import router as review_router
from api.wishlist import router as wishlist_router
from api.payments import router as payment_router
from fastapi.exceptions import RequestValidationError

models.base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)



app.include_router(auth_router)
app.include_router(users_router)
app.include_router(addresses_router)
app.include_router(category_router)
app.include_router(products_router)
app.include_router(stock_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(payment_router)
app.include_router(wishlist_router)
app.include_router(review_router)
app.include_router(admin_router)

if __name__ == "__main__":
    uvicorn.run(app, port=8000, host='127.0.0.1')

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.api import router as api_router

app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(app, port=8000, host='127.0.0.1')

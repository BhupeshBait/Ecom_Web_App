import uvicorn
from fastapi import FastAPI

from api.api import router as api_router

app = FastAPI()

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(app, port=8000, host='127.0.0.1')

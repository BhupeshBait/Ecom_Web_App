from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError



async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": str(exc.detail)})


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"success": False, "message": "Validation Error"})


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"success": False, "message": "Internal Server Error"})

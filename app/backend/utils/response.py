from fastapi.responses import JSONResponse


def success_response(message: str = "Success", data: dict | None = None):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return JSONResponse(status_code=200, content=payload)


def error_response(message: str = "Error", status_code: int = 400):
    return JSONResponse(status_code=status_code, content={"success": False, "message": message})

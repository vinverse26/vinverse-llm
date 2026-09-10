"""
Example FastAPI entrypoint. If you already have main.py, copy only the
router include and CORS lines.
"""

from fastapi import FastAPI

from auth_google import add_cors, router as auth_router

app = FastAPI(title="Vinverse API")
add_cors(app)
app.include_router(auth_router)


@app.get("/health")
def health():
    return {"ok": True}

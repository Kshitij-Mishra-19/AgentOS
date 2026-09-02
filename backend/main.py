from fastapi import FastAPI
from backend.memory.routes import router as memory_router

app = FastAPI(title="Aegis AI OS")

app.include_router(memory_router)


@app.get("/")
def root():
    return {
        "system": "Aegis AI OS",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
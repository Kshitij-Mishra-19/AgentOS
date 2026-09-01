from fastapi import FastAPI

app = FastAPI(title="Aegis AI OS")


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
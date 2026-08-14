from fastapi import FastAPI

from supportops_api.api.routes import documents_router


def create_app() -> FastAPI:
    app = FastAPI(title="SupportOps API")
    app.include_router(documents_router)
    return app


app = create_app()


@app.get("/")
def read_root():
    return {"status": "ok", "service": "supportops api"}

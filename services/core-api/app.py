from loguru import logger
from core_api.api import api_router
from fastapi import FastAPI
from core_api.wireguard.wireguard import Wireguard

app = FastAPI()
app.include_router(api_router)

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

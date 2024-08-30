from core_api.api import api_router
from fastapi import FastAPI
from core_api.storages.tokens import Tokens
from core_api.auth import new_token
from loguru import logger


def init_tokens():
    logger.info("Checking for tokens")
    if not Tokens.get_count():
        logger.info("No tokens found, creating a new one")
        logger.info(f"New token: {new_token()}")
    else:
        logger.info("Tokens found")


app = FastAPI(
    on_startup=[init_tokens],
)
app.include_router(api_router)


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

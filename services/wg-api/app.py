from wg_api.api import router
from fastapi import FastAPI
from wg_api.wireguard import Wireguard

app = FastAPI()
app.include_router(router)

default_interface = {
    "name": "gray",
    "local_ip": "10.20.30.1",
    "public_hostname": "10.10.2.4",
    "port": 51820,
    "default_dns": "10.10.10.10",
    "default_allowed_ips": "10.20.30.0/24",
    "default_persistent_keepalive": 25,
}


if __name__ == "__main__":
    import uvicorn

    wg = Wireguard()
    if not wg.get_interface_by_name(default_interface["name"]):
        wg.create_interface(**default_interface)

    uvicorn.run(app, host="0.0.0.0", port=8000)
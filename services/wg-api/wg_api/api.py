from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from .wireguard import Wireguard
from pydantic import BaseModel


class AddPeer(BaseModel):
    name: str
    address: str

    dns: str | None = None
    persistent_keepalive: int | None = None
    allowed_ips: str | None = None

class PatchPeer(BaseModel):
    name: str | None
    dns: str | None
    persistent_keepalive: int | None = None
    allowed_ips: str | None = None

wg = Wireguard()
router = APIRouter(
    tags=["Wireguard"],
    prefix="/api"
)

@router.get("/interfaces")
async def read_interfaces():
    return JSONResponse([interface.dump() for interface in wg.interfaces])

@router.get("/interfaces/{interface_name}")
async def read_interface(interface_name: str):
    interface = wg.get_interface_by_name(interface_name)
    if not interface:
        return HTTPException(status_code=404, detail="Interface not found")
    return JSONResponse(interface.dump())

@router.post("/interfaces/{interface_name}/up")
async def up_interface(interface_name: str):
    interface = wg.get_interface_by_name(interface_name)
    if not interface:
        return HTTPException(status_code=404, detail="Interface not found")
    interface.enable()
    return JSONResponse({"message": "Interface is up"})

@router.post("/interfaces/{interface_name}/down")
async def down_interface(interface_name: str):
    interface = wg.get_interface_by_name(interface_name)
    if not interface:
        return HTTPException(status_code=404, detail="Interface not found")
    interface.disable()
    return JSONResponse({"message": "Interface is down"})

@router.get("/interfaces/{interface_name}/peers")
async def read_peers(interface_name: str):
    return JSONResponse([peer.dump() for peer in wg.get_interface_by_name(interface_name).peers])

@router.put("/interfaces/{interface_name}/peers")
async def create_peer(interface_name: str, peer: AddPeer):
    interface = wg.get_interface_by_name(interface_name)
    if not interface:
        return HTTPException(status_code=404, detail="Interface not found")
    if interface.get_peer_by_address(peer.address):
        return HTTPException(status_code=409, detail="Peer with this address already exists")
    return JSONResponse(interface.create_peer(peer.name, peer.address).dump())

@router.get("/interfaces/{interface_name}/peers/{peer_id}")
async def read_peer(interface_name: str, peer_id: int):
    peer = wg.get_interface_by_name(interface_name).get_peer_by_id(peer_id)
    if not peer:
        return HTTPException(status_code=404, detail="Peer not found")
    return JSONResponse(peer.dump())

@router.delete("/interfaces/{interface_name}/peers/{peer_id}")
async def delete_peer(interface_name: str, peer_id: int):
    interface = wg.get_interface_by_name(interface_name)
    if not interface:
        return HTTPException(status_code=404, detail="Interface not found")
    peer = interface.get_peer_by_id(peer_id)
    if not peer:
        return HTTPException(status_code=404, detail="Peer not found")
    peer.delete()
    return JSONResponse({"message": "Peer deleted"})

@router.get("/interfaces/{interface_name}/peers/{peer_id}/config")
async def read_peer_config(interface_name: str, peer_id: int):
    peer = wg.get_interface_by_name(interface_name).get_peer_by_id(peer_id)
    if not peer:
        return HTTPException(status_code=404, detail="Peer not found")
    return PlainTextResponse(peer.config)
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from .wireguard import Wireguard, Interface, Peer
from pydantic import BaseModel
from .auth import check_token


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
    prefix="/api",
    dependencies=[Depends(check_token)]
)

def interfaceDep(interface_name: str) -> Interface:
    interface = wg.get_interface_by_name(interface_name)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface not found")
    return interface

def peerDep(interface: Annotated[Interface, Depends(interfaceDep)], peer_id: int) -> Peer:
    peer = interface.get_peer_by_id(peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    return peer

@router.get("/interfaces")
async def read_interfaces():
    return JSONResponse([interface.dump() for interface in wg.interfaces])

@router.get("/interfaces/{interface_name}")
async def read_interface(interface: Interface = Depends(interfaceDep)):
    return JSONResponse(interface.dump())

@router.post("/interfaces/{interface_name}/up")
async def up_interface(interface: Annotated[Interface, Depends(interfaceDep)]):
    interface.enable()
    return JSONResponse({"message": "Interface is up"})

@router.post("/interfaces/{interface_name}/down")
async def down_interface(interface: Annotated[Interface, Depends(interfaceDep)]):
    interface.disable()
    return JSONResponse({"message": "Interface is down"})

@router.get("/interfaces/{interface_name}/peers")
async def read_peers(interface: Annotated[Interface, Depends(interfaceDep)]):
    return JSONResponse([peer.dump() for peer in interface.peers])

@router.put("/interfaces/{interface_name}/peers")
async def create_peer(interface: Annotated[Interface, Depends(interfaceDep)], peer: AddPeer):
    if interface.get_peer_by_address(peer.address):
        return HTTPException(status_code=409, detail="Peer with this address already exists")
    return JSONResponse(interface.create_peer(peer.name, peer.address).dump())

@router.get("/interfaces/{interface_name}/peers/{peer_id}")
async def read_peer(peer: Annotated[Peer, Depends(peerDep)]):
    return JSONResponse(peer.dump())

@router.delete("/interfaces/{interface_name}/peers/{peer_id}")
async def delete_peer(peer: Annotated[Peer, Depends(peerDep)]):
    peer.delete()
    return JSONResponse({"message": "Peer deleted"})

@router.get("/interfaces/{interface_name}/peers/{peer_id}/config")
async def read_peer_config(peer: Annotated[Peer, Depends(peerDep)]):
    return PlainTextResponse(peer.config)
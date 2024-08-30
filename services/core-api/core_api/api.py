from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from .wireguard.wireguard import Wireguard, Interface, Peer
from .pihole.connector import PiHole
from pydantic import BaseModel, Field
from .auth import new_token, renew_token, remove_token
from ipaddress import IPv4Address, IPv4Network, IPv4Interface, IPv6Network


class CreatePeer(BaseModel):
    name: str
    address: IPv4Address

    dns: str | None = None
    persistent_keepalive: int | None = None
    allowed_ips: list[IPv4Network | IPv6Network] | None = None


class CreateInterface(BaseModel):
    name: str = "wg0"
    local_ip: IPv4Interface = IPv4Interface("10.20.30.1/24")
    public_host: str = "localhost"
    listen_port: int = 51820

    default_dns: str = "1.1.1.1"
    default_allowed_ips: list[IPv4Network | IPv6Network] = [
        IPv4Network("0.0.0.0/0"),
        IPv6Network("::/0"),
    ]

    default_persistent_keepalive: int = 25


class PatchPeer(BaseModel):
    name: str | None
    dns: str | None
    persistent_keepalive: int | None = None
    allowed_ips: list[IPv4Network | IPv6Network] | None = None


wg = Wireguard()
ph = PiHole()

api_router = APIRouter(tags=["Wireguard"], prefix="/api")

interfaces_router = APIRouter(
    tags=["Interfaces"],
    prefix="/interfaces",
    # dependencies=[Depends(check_token)],
)


async def interfaceDep(interface_id: int) -> Interface:
    interface = wg.get_interface(interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface not found")
    return interface


async def peerDep(peer_id: int) -> Peer:
    peer = wg.get_peer(peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    return peer


@interfaces_router.get("/", response_model=list[Interface])
async def read_interfaces():
    return [interface for interface in wg.interfaces]


@interfaces_router.put("/", response_model=Interface)
async def create_interface(model: CreateInterface) -> Interface:
    return wg.create_interface(
        name=model.name,
        local_ip=model.local_ip,
        public_hostname=model.public_host,
        port=model.listen_port,
        default_dns=model.default_dns,
        default_allowed_ips=model.default_allowed_ips,
        default_persistent_keepalive=model.default_persistent_keepalive,
    )


@interfaces_router.get("/{interface_id}", response_model=Interface)
async def read_interface(
    interface: Interface = Depends(interfaceDep),
) -> Interface:
    return interface


@interfaces_router.delete("/{interface_id}")
async def delete_interface(
    interface: Annotated[Interface, Depends(interfaceDep)]
) -> JSONResponse:
    wg.delete_interface(interface)
    return JSONResponse({"message": "Interface deleted"})


@interfaces_router.post("/{interface_id}/up")
async def up_interface(
    interface: Annotated[Interface, Depends(interfaceDep)]
) -> JSONResponse:
    wg.up_interface(interface)
    return JSONResponse({"message": "Interface is up"})


@interfaces_router.post("/{interface_id}/down")
async def down_interface(
    interface: Annotated[Interface, Depends(interfaceDep)]
) -> JSONResponse:
    wg.down_interface(interface)
    return JSONResponse({"message": "Interface is down"})


@interfaces_router.get("/{interface_id}/peers", response_model=list[Peer])
async def read_peers(
    interface: Annotated[Interface, Depends(interfaceDep)],
    fill_defaults: bool = True,
    fill_stats: bool = True,
) -> list[Peer]:
    result = wg.get_peers(interface)
    result = wg.fill_peers_defaults(result) if fill_defaults else result
    result = wg.fill_peers_stats(result) if fill_stats else result
    return result


@interfaces_router.put("/{interface_name}/peers", response_model=Peer)
async def create_peer(
    interface: Annotated[Interface, Depends(interfaceDep)], peer: CreatePeer
):
    if wg.get_peer_by_address(interface, peer.address):
        raise HTTPException(
            status_code=409, detail="Peer with this address already exists"
        )

    return wg.create_peer(
        interface=interface,
        name=peer.name,
        address=peer.address,
        remote_dns=peer.dns,
        remote_persistent_keepalive=peer.persistent_keepalive,
        remote_allowed_ips=peer.allowed_ips,
    )


api_router.include_router(interfaces_router)

peers_router = APIRouter(
    tags=["Peers"],
    prefix="/peers",
    # dependencies=[Depends(check_token)],
)


@peers_router.get("/{peer_id}", response_model=Peer)
async def read_peer(
    peer: Annotated[Peer, Depends(peerDep)],
    fill_defaults: bool = True,
    fill_stats: bool = True,
) -> Peer:
    peer = wg.fill_peer_defaults(peer) if fill_defaults else peer
    peer = wg.fill_peer_stats(peer) if fill_stats else peer
    return peer


@peers_router.delete("/{peer_id}")
async def delete_peer(peer: Annotated[Peer, Depends(peerDep)]) -> JSONResponse:
    wg.delete_peer(peer)
    return JSONResponse({"message": "Peer deleted"})


@peers_router.get("/{peer_id}/config")
async def read_peer_config(
    peer: Annotated[Peer, Depends(peerDep)]
) -> PlainTextResponse:
    return PlainTextResponse(wg.get_config(peer))


api_router.include_router(peers_router)

token_router = APIRouter(
    tags=["Token"],
    prefix="/token",
    # dependencies=[Depends(check_token)]
)


@token_router.post("/token/new")
async def request_new_token() -> JSONResponse:
    return JSONResponse({"token": new_token()})


@token_router.post("token/{token}/renew")
async def request_renew_token(token: str) -> JSONResponse:
    return JSONResponse({"token": renew_token(token)})


@token_router.delete("token/{token}")
async def request_remove_token(token: str) -> JSONResponse:
    remove_token(token)
    return JSONResponse({"message": "Token removed"})


api_router.include_router(interfaces_router)


dns_router = APIRouter(
    tags=["DNS"],
    prefix="/dns",
    # dependencies=[Depends(check_token)]
)


@dns_router.get("/rewrites")
async def read_dns_rewrites() -> JSONResponse:
    return JSONResponse(
        [{"domain": rewrite.domain, "ip": rewrite.ip} for rewrite in ph.get_rewrites()]
    )


@dns_router.get("/rewrites/{domain}")
async def read_dns_rewrite(domain: str) -> JSONResponse:
    rewrite = ph.find_rewrite(domain)
    if not rewrite:
        raise HTTPException(status_code=404, detail="Domain not found")
    return JSONResponse({"domain": rewrite.domain, "ip": rewrite.ip})


@dns_router.post("/rewrites")
async def add_dns_rewrite(domain: str, ip: IPv4Address) -> JSONResponse:
    if ph.find_rewrite(domain):
        raise HTTPException(status_code=409, detail="Domain already exists")
    ph.add_rewrite(domain, ip)
    return JSONResponse({"message": "Rewrite added"})


@dns_router.delete("/rewrites/{domain}")
async def remove_dns_rewrite(domain: str) -> JSONResponse:
    if not ph.find_rewrite(domain):
        raise HTTPException(status_code=404, detail="Domain does not exist")
    ph.remove_rewrite(domain)
    return JSONResponse({"message": "Rewrite removed"})


api_router.include_router(dns_router)

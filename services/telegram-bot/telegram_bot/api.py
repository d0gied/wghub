from functools import wraps
from aiohttp import ClientSession
from .config import Config
from pydantic import BaseModel
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Network


class CreatePeer(BaseModel):
    name: str
    address: IPv4Address

    dns: str | None = None
    persistent_keepalive: int | None = None
    allowed_ips: list[IPv4Network | IPv6Network] | None = None


class Interface(BaseModel):
    id: int
    name: str
    local_ip: IPv4Interface
    public_hostname: str
    port: int

    public_key: str
    private_key: str
    pre_up: str
    post_up: str
    pre_down: str
    post_down: str

    default_dns: str
    default_allowed_ips: list[IPv4Network | IPv6Network]
    default_persistent_keepalive: int

    enabled: bool


class Peer(BaseModel):
    id: int
    interface_id: int

    name: str
    public_key: str
    private_key: str
    preshared_key: str
    address: IPv4Address
    allowed_ips: list[IPv4Network | IPv6Network] | None

    remote_allowed_ips: list[IPv4Network | IPv6Network] | None
    remote_dns: str | None
    remote_persistent_keepalive: int | None

    latest_handshake: int | None = None
    transfer_rx: int | None = None
    transfer_tx: int | None = None


class WireguardApi:

    @staticmethod
    def session_wrapper(func):

        @wraps(func)
        async def wrapper(self: "WireguardApi", *args, **kwargs):
            if not self.session_open:
                async with self:
                    return await func(self, *args, **kwargs)
            else:
                return await func(self, *args, **kwargs)

        return wrapper

    def __init__(
        self,
        host: str = Config.WireguardApi.HOST,
        port: int = Config.WireguardApi.PORT,
        auth_token: str = Config.WireguardApi.AUTH_TOKEN,
    ):
        self.host = host
        self.port = port

        self.headers = {
            "Authorization": f"Bearer {auth_token}",
        }
        self._session: ClientSession
        self.session_open = False

    def _get_url(self, path: str) -> str:
        return f"http://{self.host}:{self.port}/api/{path}"

    async def __aenter__(self) -> "WireguardApi":
        self._session = ClientSession(headers=self.headers)
        self.session_open = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._session.close()
        self.session_open = False

    async def _get(self, path: str) -> dict:
        return await (await self._session.get(self._get_url(path))).json()

    async def _get_raw(self, path: str) -> str:
        return await (await self._session.get(self._get_url(path))).text()

    async def _post(self, path: str, *, data: dict | BaseModel | None = None) -> dict:
        _data = data.model_dump_json() if isinstance(data, BaseModel) else data
        return await (await self._session.post(self._get_url(path), json=_data)).json()

    async def _put(self, path: str, *, data: dict | BaseModel | None = None) -> dict:
        _data = data.model_dump_json() if isinstance(data, BaseModel) else data
        return await (await self._session.put(self._get_url(path), json=_data)).json()

    async def _delete(self, path: str) -> dict:
        return await (await self._session.delete(self._get_url(path))).json()

    @session_wrapper
    async def get_interfaces(self) -> list[Interface]:
        return [
            Interface.model_validate(interface)
            for interface in (await self._get("interfaces"))
        ]

    @session_wrapper
    async def get_interface(self, interface_id: int) -> Interface:
        return Interface.model_validate(await self._get(f"interfaces/{interface_id}"))

    @session_wrapper
    async def up_interface(self, interface_id: int) -> dict:
        return await self._post(f"interfaces/{interface_id}/up")

    @session_wrapper
    async def down_interface(self, interface_id: int) -> dict:
        return await self._post(f"interfaces/{interface_id}/down")

    @session_wrapper
    async def get_peers(self, interface_id: int) -> list[Peer]:
        return [
            Peer.model_validate(peer)
            for peer in (await self._get(f"interfaces/{interface_id}/peers"))
        ]

    @session_wrapper
    async def create_peer(self, interface_id: int, peer: CreatePeer) -> Peer:
        return Peer.model_validate(
            await self._put(f"interfaces/{interface_id}/peers", data=peer)
        )

    @session_wrapper
    async def get_peer(self, peer_id: int) -> Peer:
        return Peer.model_validate(await self._get(f"peers/{peer_id}"))

    @session_wrapper
    async def delete_peer(self, peer_id: int) -> dict:
        return await self._delete(f"peers/{peer_id}")

    @session_wrapper
    async def get_peer_config(self, peer_id: int) -> str:
        return await self._get_raw(f"peers/{peer_id}/config")

    @session_wrapper
    async def request_new_token(self) -> dict:
        return (await self._post("token/new"))["token"]

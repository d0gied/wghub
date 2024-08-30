from typing import Self


class Block:
    def __init__(self, name: str) -> None:
        self._block_name: str = name
        self._params: dict[str, str] = {}

    def build(self) -> str:
        return "\n".join(
            [
                f"[{self._block_name}]",
                *(f"{key} = {value}" for key, value in self._params.items() if value),
            ]
        )

    def set_param(self, key: str, value: str) -> Self:
        self._params[key] = value
        return self

    def update(self, **kwargs) -> Self:
        for key, value in kwargs.items():
            self.set_param(key, value)
        return self

    @staticmethod
    def join(blocks: list["Block"]) -> str:
        return "\n\n".join(block.build().strip() for block in blocks)


class PeerBuilder(Block):
    def __init__(self) -> None:
        super().__init__("Peer")

    def public_key(self, key: str) -> Self:
        return self.set_param("PublicKey", key)

    def allowed_ips(self, ips: str) -> Self:
        return self.set_param("AllowedIPs", ips)
    
    def endpoint(self, endpoint: str) -> Self:
        return self.set_param("Endpoint", endpoint)

    def preshared_key(self, key: str) -> Self:
        return self.set_param("PresharedKey", key)
    
    def persistent_keepalive(self, interval: int) -> Self:
        return self.set_param("PersistentKeepalive", str(interval))


class InterfaceBuilder(Block):
    def __init__(self, name: str) -> None:
        super().__init__("Interface")
        self.name = name
        self.peers: list[PeerBuilder] = []

    def address(self, address: str) -> Self:
        return self.set_param("Address", address)

    def listen_port(self, port: str) -> Self:
        return self.set_param("ListenPort", port)
    
    def allowed_ips(self, ips: str) -> Self:
        return self.set_param("AllowedIPs", ips)

    def private_key(self, key: str) -> Self:
        return self.set_param("PrivateKey", key)

    def pre_up(self, command: str) -> Self:
        return self.set_param("PreUp", command)

    def post_up(self, command: str) -> Self:
        return self.set_param("PostUp", command)

    def pre_down(self, command: str) -> Self:
        return self.set_param("PreDown", command)

    def post_down(self, command: str) -> Self:
        return self.set_param("PostDown", command)
    
    def dns(self, dns: str) -> Self:
        return self.set_param("DNS", dns)
    
    def build(self) -> str:
        return self.join([super(), *self.peers])

    def add_peer(self, peer: PeerBuilder) -> Self:
        self.peers.append(peer)
        return self
      
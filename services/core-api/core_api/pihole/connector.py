from dataclasses import dataclass
from ipaddress import IPv4Address


CONFIG_PATH = "/etc/pihole/custom.list"


@dataclass
class DNSRewrite:
    domain: str
    ip: IPv4Address

    def __str__(self) -> str:
        return f"{self.ip} {self.domain}"

    @classmethod
    def from_line(cls, line: str) -> "DNSRewrite":
        ip, domain = line.split()
        return cls(domain, IPv4Address(ip))


class PiHole:
    def __init__(self, config_path: str = CONFIG_PATH) -> None:
        self.rewrites: dict[str, IPv4Address] = {}  # domain: ip
        self.config_path = config_path

    def _load_rewrites(self) -> None:
        with open(self.config_path, "r") as f:
            self.rewrites = {
                rewrite.domain: rewrite.ip
                for rewrite in (
                    DNSRewrite.from_line(line) for line in f.readlines() if line.strip()
                )
            }

    def _save_rewrites(self) -> None:
        with open(self.config_path, "w") as f:
            f.write("\n".join(f"{ip} {host}" for host, ip in self.rewrites.items()))

    def add_rewrite(self, domain: str, ip: IPv4Address) -> None:
        if domain in self.rewrites:
            raise ValueError("Domain already exists")
        self.rewrites[domain] = ip
        self._save_rewrites()

    def remove_rewrite(self, domain: str) -> None:
        if domain not in self.rewrites:
            raise ValueError("Domain does not exist")
        del self.rewrites[domain]
        self._save_rewrites()

    def find_rewrite(self, domain: str) -> DNSRewrite | None:
        self._load_rewrites()
        return (
            DNSRewrite(domain, self.rewrites[domain])
            if domain in self.rewrites
            else None
        )

    def get_rewrites(self) -> list[DNSRewrite]:
        self._load_rewrites()
        return [DNSRewrite(domain, ip) for domain, ip in self.rewrites.items()]

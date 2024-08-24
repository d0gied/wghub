from .storage import InterfaceModel, Storage
from python_wireguard import Server, Key, ClientConnection
from multiprocessing import Process
from loguru import logger

class Wireguard:
    def __init__(self) -> None:
        self.storage = Storage("wg.db")
        self.servers: dict[str, Server]
        self.processes: dict[str, Process]

    def load_interface(self, interface_name: str) -> bool:
        logger.info(f"Loading interface {interface_name}")
        interface = self.storage.get_interface_by_name(interface_name)
        if not interface:
            logger.error(f"Interface {interface_name} not found")
            return False
        peers = self.storage.get_peers_by_interface_id(interface.id)
        logger.info(f"Found {len(peers)} peers for interface {interface_name}")
        server = Server(
            interface_name=interface.interface_name,
            local_ip=interface.local_ip,
            key=Key(interface.private_key),
            port=interface.port,
        )
        for peer in peers:
            server.add_client(
                ClientConnection(
                    public_key=peer.public_key,
                    local_ip=peer.address
                )
            )
            logger.info(f"Added peer {peer.name} to interface {interface_name}")
        self.servers[interface_name] = server
        logger.info(f"Loaded interface {interface_name}")
        return True

    def load(self):
        self.servers = {}
        interfaces = self.storage.get_interfaces()
        logger.info(f"Found {len(interfaces)} interfaces")
        for interface in interfaces:
            self.load_interface(interface.interface_name)
        logger.info("Loaded all interfaces")

    def start_interface(self, interface_name: str) -> bool:
        logger.info(f"Starting interface {interface_name}")
        if interface_name in self.processes:
            logger.warning(f"Interface {interface_name} already started")
            return False
        server = self.servers.get(interface_name)
        if not server:
            logger.error(f"Interface {interface_name} not found")
            return False
        server.create_interface()
        logger.info(f"Created interface {interface_name}")
        process = Process(target=server.enable)
        process.start()
        self.processes[interface_name] = process
        logger.info(f"Started interface {interface_name}")
        return True
        
    def stop_interface(self, interface_name: str) -> bool:
        logger.info(f"Stopping interface {interface_name}")
        if interface_name not in self.processes:
            logger.warning(f"Interface {interface_name} not started")
            return False
        process = self.processes.pop(interface_name)
        process.terminate()
        logger.info(f"Terminated process for interface {interface_name}")
        self.servers[interface_name].delete_interface()
        logger.info(f"Deleted interface {interface_name}")

        return True
    
    def reload_interface(self, interface_name: str) -> bool:
        logger.info(f"Reloading interface {interface_name}")
        if interface_name not in self.processes:
            logger.warning(f"Interface {interface_name} not started")
            return False
        self.stop_interface(interface_name)
        self.load_interface(interface_name)
        self.start_interface(interface_name)
        logger.info(f"Reloaded interface {interface_name}")
        return True

    def start_all(self):
        logger.info("Starting all interfaces")
        for interface_name in self.servers:
            if interface_name not in self.processes:
                self.start_interface(interface_name)
        
    def stop_all(self):
        logger.info("Stopping all interfaces")
        for interface_name in self.processes:
            self.stop_interface(interface_name)

    def reload_all(self):
        logger.info("Reloading all interfaces")
        self.stop_all()
        self.load()
        self.start_all()
    

    def create_interface(self, interface_name: str, local_ip: str, port: int) -> bool:
        logger.info(f"Creating interface {interface_name}")
        if self.storage.get_interface_by_name(interface_name):
            logger.error(f"Interface {interface_name} already exists")
            return False
        private, public = Key.key_pair()
        self.storage.insert_interface(
            InterfaceModel(
                interface_name=interface_name,
                local_ip=local_ip,
                port=port,
                private_key=private,
                public_key=public,
            )
        )
        logger.info(f"Created interface {interface_name}")
        self.load_interface(interface_name)
        return True


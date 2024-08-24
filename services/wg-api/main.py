from wg_api import wireguard, storage


if __name__ == "__main__":
    wg = wireguard.Wireguard()
    wg.create_interface(
        interface_name="wg0",
        local_ip="10.10.0.1/24",
        port=51820,
    )
    wg.enable()

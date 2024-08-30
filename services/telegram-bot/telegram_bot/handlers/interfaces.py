import io
from ipaddress import IPv4Address
from aiogram import types
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from ..api import CreatePeer, WireguardApi, Interface, Peer
from . import Router
from loguru import logger
import qrcode

wg_api = WireguardApi()
router = Router(name="interfaces")


class InterfaceCallbackData(CallbackData, prefix="interface"):
    interface: int


class PeerCallbackData(CallbackData, prefix="peer"):
    peer: int


class DeletePeerCallbackData(CallbackData, prefix="delete_peer"):
    peer: int


class CreatePeerCallbackData(CallbackData, prefix="create_peer"):
    interface: int


class QRCodeCallbackData(CallbackData, prefix="qrcode"):
    peer: int


class ShowConfigCallbackData(CallbackData, prefix="show_config"):
    peer: int


class DownloadConfigCallbackData(CallbackData, prefix="download_config"):
    peer: int


@router.message(Command("interfaces"))
async def interfaces(message: types.Message):
    text = "Interfaces:\n"
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=interface.name,
                    callback_data=InterfaceCallbackData(interface=interface.id).pack(),
                )
            ]
            for interface in await wg_api.get_interfaces()
        ]
    )
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(InterfaceCallbackData.filter())
async def interface_info(
    query: types.CallbackQuery, callback_data: InterfaceCallbackData
):
    message = query.message
    if isinstance(message, types.InaccessibleMessage) or not message:
        logger.warning("Message is inaccessible")
        return

    async with (
        wg_api
    ):  # This is a context manager that will close the session after the block
        interface = await wg_api.get_interface(callback_data.interface)
        text = f"Interface {interface.name}:\n"
        text += f"Peer count: {len(await wg_api.get_peers(interface.id))}\n"
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Create peer",
                        callback_data=CreatePeerCallbackData(
                            interface=interface.id
                        ).pack(),
                    )
                ]
            ]
            + [
                [
                    types.InlineKeyboardButton(
                        text=f"{peer.name} ({peer.address})",
                        callback_data=PeerCallbackData(peer=peer.id).pack(),
                    )
                ]
                for peer in await wg_api.get_peers(interface.id)
            ]
        )

    await message.edit_text(text, reply_markup=keyboard)


@router.callback_query(CreatePeerCallbackData.filter())
async def create_peer(
    query: types.CallbackQuery, callback_data: CreatePeerCallbackData
):
    message = query.message
    if isinstance(message, types.InaccessibleMessage) or not message:
        logger.warning("Message is inaccessible")
        return

    async with wg_api:
        interface = await wg_api.get_interface(callback_data.interface)
        peers = await wg_api.get_peers(interface.id)
        network = interface.local_ip.network
        used_addresses = {peer.address for peer in peers}

        free_address: IPv4Address
        for host in network.hosts():
            if host in used_addresses:
                continue
            free_address = host
            break
        else:
            raise ValueError("No free addresses available")

        peer = await wg_api.create_peer(
            interface.id,
            CreatePeer(
                name="Unknown",
                address=free_address,
                persistent_keepalive=25,
            ),
        )

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Back",
                    callback_data=InterfaceCallbackData(interface=interface.id).pack(),
                )
            ]
        ]
    )

    await message.edit_text(
        f"Peer created with address {peer.address}", reply_markup=keyboard
    )


@router.callback_query(PeerCallbackData.filter())
async def peer_info(query: types.CallbackQuery, callback_data: PeerCallbackData):
    message = query.message
    if isinstance(message, types.InaccessibleMessage) or not message:
        logger.warning("Message is inaccessible")
        return

    async with wg_api:
        peer = await wg_api.get_peer(callback_data.peer)
        interface = await wg_api.get_interface(peer.interface_id)
        text = f"Peer {peer.id}:\n"
        text += f"Public key: {peer.public_key}\n"
        text += f"Allowed IPs: {peer.allowed_ips}\n"

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="QR Code",
                    callback_data=QRCodeCallbackData(peer=peer.id).pack(),
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="Show Config",
                    callback_data=ShowConfigCallbackData(peer=peer.id).pack(),
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="Download Config",
                    callback_data=DownloadConfigCallbackData(peer=peer.id).pack(),
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="Delete",
                    callback_data=DeletePeerCallbackData(peer=peer.id).pack(),
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Back",
                    callback_data=InterfaceCallbackData(interface=interface.id).pack(),
                ),
            ],
        ]
    )

    await message.edit_text(text, reply_markup=keyboard)


@router.callback_query(DeletePeerCallbackData.filter())
async def delete_peer(
    query: types.CallbackQuery, callback_data: DeletePeerCallbackData
):
    message = query.message
    if isinstance(message, types.InaccessibleMessage) or not message:
        logger.warning("Message is inaccessible")
        return

    async with wg_api:
        peer = await wg_api.get_peer(callback_data.peer)
        interface = await wg_api.get_interface(peer.interface_id)
        await wg_api.delete_peer(peer.id)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Back",
                    callback_data=InterfaceCallbackData(interface=interface.id).pack(),
                )
            ]
        ]
    )

    await message.edit_text("Peer deleted", reply_markup=keyboard)


@router.callback_query(QRCodeCallbackData.filter())
async def qr_code(query: types.CallbackQuery, callback_data: QRCodeCallbackData):
    message = query.message
    if isinstance(message, types.InaccessibleMessage) or not message:
        logger.warning("Message is inaccessible")
        return

    async with wg_api:
        peer = await wg_api.get_peer(callback_data.peer)
        interface = await wg_api.get_interface(peer.interface_id)
        config = await wg_api.get_peer_config(peer.id)

    buffer = io.BytesIO()
    qr_code = qrcode.make(data=config).save(buffer)
    await message.answer_photo(
        types.BufferedInputFile(
            file=buffer.getvalue(),
            filename="qr_code.png",
        ),
        caption=f"QR Code for {interface.name}: {peer.name} ({peer.address})",
    )
    await message.delete()


@router.callback_query(ShowConfigCallbackData.filter())
async def show_config(
    query: types.CallbackQuery, callback_data: ShowConfigCallbackData
):
    message = query.message
    if isinstance(message, types.InaccessibleMessage) or not message:
        logger.warning("Message is inaccessible")
        return

    async with wg_api:
        peer = await wg_api.get_peer(callback_data.peer)
        config = await wg_api.get_peer_config(peer.id)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Back",
                    callback_data=PeerCallbackData(peer=peer.id).pack(),
                )
            ]
        ]
    )

    await message.edit_text(
        f"```toml\n{config}\n```", reply_markup=keyboard, parse_mode="MarkdownV2"
    )


@router.callback_query(DownloadConfigCallbackData.filter())
async def download_config(
    query: types.CallbackQuery, callback_data: DownloadConfigCallbackData
):
    message = query.message
    if isinstance(message, types.InaccessibleMessage) or not message:
        logger.warning("Message is inaccessible")
        return

    async with wg_api:
        peer = await wg_api.get_peer(callback_data.peer)
        interface = await wg_api.get_interface(peer.interface_id)
        config = await wg_api.get_peer_config(peer.id)

    await message.answer_document(
        types.BufferedInputFile(
            file=config.encode(),
            filename=f"{interface.name}_{peer.id}.conf",
        )
    )
    await message.delete()

"""
Process-Ontological Secure Transport (POST) Asyncio Socket Proxy Middleware
Provides zero-overhead, transparent TCP proxying encrypted via POST non-Hermitian phase streams.
"""

import asyncio
import logging
import struct
from typing import Optional
from .post_crypto import PostCryptoEngine, HEADER_SIZE, HEADER_STRUCT_FMT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("POST_Proxy")

class PostClientProxy:
    """
    Client-side POST Proxy.
    Accepts plain TCP connections locally and wraps traffic in POST frames over wire.
    """
    def __init__(
        self,
        local_host: str,
        local_port: int,
        remote_host: str,
        remote_port: int,
        seed: bytes,
        stream_id: int = 1001,
    ):
        self.local_host = local_host
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.seed = seed
        self.stream_id = stream_id
        self.server: Optional[asyncio.AbstractServer] = None

    async def handle_client(self, app_reader: asyncio.StreamReader, app_writer: asyncio.StreamWriter):
        logger.info(f"Client proxy accepted application connection from {app_writer.get_extra_info('peername')}")
        
        try:
            wire_reader, wire_writer = await asyncio.open_connection(self.remote_host, self.remote_port)
        except Exception as e:
            logger.error(f"Failed to connect to remote POST server {self.remote_host}:{self.remote_port}: {e}")
            app_writer.close()
            await app_writer.wait_closed()
            return

        tx_engine = PostCryptoEngine(seed=self.seed)
        rx_engine = PostCryptoEngine(seed=self.seed)
        seq_out = 0

        async def app_to_wire():
            nonlocal seq_out
            while True:
                data = await app_reader.read(4096)
                if not data:
                    break
                frame = tx_engine.encrypt_frame(data, stream_id=self.stream_id, seq_num=seq_out)
                seq_out += 1
                wire_writer.write(frame)
                await wire_writer.drain()
            wire_writer.close()
            await wire_writer.wait_closed()

        async def wire_to_app():
            while True:
                try:
                    header_data = await wire_reader.readexactly(HEADER_SIZE)
                except asyncio.IncompleteReadError:
                    break
                if not header_data:
                    break
                
                payload_len = struct.unpack(">I", header_data[56:60])[0]
                try:
                    ciphertext = await wire_reader.readexactly(payload_len)
                except asyncio.IncompleteReadError:
                    break
                
                full_frame = header_data + ciphertext
                plaintext, _, _, _ = rx_engine.decrypt_frame(full_frame)
                
                app_writer.write(plaintext)
                await app_writer.drain()
            app_writer.close()
            await app_writer.wait_closed()

        task1 = asyncio.create_task(app_to_wire())
        task2 = asyncio.create_task(wire_to_app())
        done, pending = await asyncio.wait([task1, task2], return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        app_writer.close()
        wire_writer.close()

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.local_host, self.local_port)
        logger.info(f"POST Client Proxy listening on plain TCP {self.local_host}:{self.local_port} -> {self.remote_host}:{self.remote_port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("POST Client Proxy stopped")


class PostServerProxy:
    """
    Server-side POST Proxy.
    Accepts POST encrypted frames from wire, deciphers, and proxies raw TCP to backend.
    """
    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        backend_host: str,
        backend_port: int,
        seed: bytes,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.backend_host = backend_host
        self.backend_port = backend_port
        self.seed = seed
        self.server: Optional[asyncio.AbstractServer] = None

    async def handle_wire(self, wire_reader: asyncio.StreamReader, wire_writer: asyncio.StreamWriter):
        logger.info(f"Server proxy accepted POST wire connection from {wire_writer.get_extra_info('peername')}")
        
        try:
            backend_reader, backend_writer = await asyncio.open_connection(self.backend_host, self.backend_port)
        except Exception as e:
            logger.error(f"Failed to connect to target backend {self.backend_host}:{self.backend_port}: {e}")
            wire_writer.close()
            await wire_writer.wait_closed()
            return

        rx_engine = PostCryptoEngine(seed=self.seed)
        tx_engine = PostCryptoEngine(seed=self.seed)
        seq_out = 0

        async def wire_to_backend():
            while True:
                try:
                    header_data = await wire_reader.readexactly(HEADER_SIZE)
                except asyncio.IncompleteReadError:
                    break
                
                payload_len = struct.unpack(">I", header_data[56:60])[0]
                ciphertext = await wire_reader.readexactly(payload_len)
                
                full_frame = header_data + ciphertext
                try:
                    plaintext, stream_id, seq_num, flags = rx_engine.decrypt_frame(full_frame)
                except ValueError as ve:
                    logger.error(f"Decryption/Verification failure: {ve}. Terminating wire connection!")
                    break
                
                backend_writer.write(plaintext)
                await backend_writer.drain()
                
            backend_writer.close()
            await backend_writer.wait_closed()

        async def backend_to_wire():
            nonlocal seq_out
            while True:
                data = await backend_reader.read(4096)
                if not data:
                    break
                frame = tx_engine.encrypt_frame(data, stream_id=9999, seq_num=seq_out)
                seq_out += 1
                wire_writer.write(frame)
                await wire_writer.drain()
            wire_writer.close()
            await wire_writer.wait_closed()

        task1 = asyncio.create_task(wire_to_backend())
        task2 = asyncio.create_task(backend_to_wire())
        done, pending = await asyncio.wait([task1, task2], return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        wire_writer.close()
        backend_writer.close()

    async def start(self):
        self.server = await asyncio.start_server(self.handle_wire, self.listen_host, self.listen_port)
        logger.info(f"POST Server Proxy listening on wire {self.listen_host}:{self.listen_port} -> backend {self.backend_host}:{self.backend_port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("POST Server Proxy stopped")

"""
Comprehensive Test Suite for Process-Ontological Secure Transport (POST) Middleware.
"""

import os
import sys
import asyncio
import pytest

# Ensure src/ is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.post_crypto import PhaseAttractor, PostCryptoEngine
from src.post_proxy import PostClientProxy, PostServerProxy
from src.telemetry import PostTelemetry

def test_phase_attractor_evolution():
    seed = os.urandom(32)
    p1 = PhaseAttractor(seed=seed)
    d1 = p1.compute_digest()
    
    assert len(d1) == 32
    assert p1.seq == 0
    
    # Evolve state
    p1.evolve()
    d2 = p1.compute_digest()
    assert p1.seq == 1
    assert d1 != d2

def test_encrypt_decrypt_roundtrip():
    seed = os.urandom(32)
    tx = PostCryptoEngine(seed=seed)
    rx = PostCryptoEngine(seed=seed)
    
    payload = b"Process Ontology: Boundary Flux Secure Transmission Baseline"
    frame = tx.encrypt_frame(payload, stream_id=42, seq_num=0)
    
    decrypted, stream_id, seq_num, flags = rx.decrypt_frame(frame)
    assert decrypted == payload
    assert stream_id == 42
    assert seq_num == 0

def test_mitm_perturbation_detection():
    seed = os.urandom(32)
    tx = PostCryptoEngine(seed=seed)
    rx = PostCryptoEngine(seed=seed)
    
    payload = b"Secret payload target for MITM interception test"
    frame = tx.encrypt_frame(payload, stream_id=1, seq_num=0)
    
    # Inject MITM perturbation into receiver's phase engine
    rx.attractor.inject_mitm_perturbation()
    
    with pytest.raises(ValueError, match="Phase Coherence Breakdown"):
        rx.decrypt_frame(frame)

def test_hmac_tamper_detection():
    seed = os.urandom(32)
    tx = PostCryptoEngine(seed=seed)
    rx = PostCryptoEngine(seed=seed)
    
    payload = b"Tamper resilience test payload"
    frame = bytearray(tx.encrypt_frame(payload, stream_id=1, seq_num=0))
    
    # Corrupt last byte of ciphertext payload
    frame[-1] ^= 0xFF
    
    with pytest.raises(ValueError):
        rx.decrypt_frame(bytes(frame))

def test_async_proxy_end_to_end():
    async def _async_test():
        seed = os.urandom(32)
        
        # 1. Start Mock Backend Echo Server
        backend_received = []
        async def handle_backend(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            data = await reader.read(4096)
            backend_received.append(data)
            writer.write(b"ECHO: " + data)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        backend_server = await asyncio.start_server(handle_backend, "127.0.0.1", 19991)
        
        # 2. Start POST Server Proxy (Listen on 19992 -> Forward to Backend 19991)
        server_proxy = PostServerProxy(
            listen_host="127.0.0.1",
            listen_port=19992,
            backend_host="127.0.0.1",
            backend_port=19991,
            seed=seed,
        )
        await server_proxy.start()
        
        # 3. Start POST Client Proxy (Listen on 19993 -> Forward to Wire Server Proxy 19992)
        client_proxy = PostClientProxy(
            local_host="127.0.0.1",
            local_port=19993,
            remote_host="127.0.0.1",
            remote_port=19992,
            seed=seed,
        )
        await client_proxy.start()
        
        await asyncio.sleep(0.1)
        
        # 4. Client Application connects to Client Proxy on 19993
        app_reader, app_writer = await asyncio.open_connection("127.0.0.1", 19993)
        test_msg = b"Hello POST World! Hydrodynamic stream test."
        app_writer.write(test_msg)
        await app_writer.drain()
        
        response = await app_reader.read(4096)
        assert response == b"ECHO: " + test_msg
        assert backend_received[0] == test_msg
        
        app_writer.close()
        await app_writer.wait_closed()
        
        # Cleanup
        await client_proxy.stop()
        await server_proxy.stop()
        backend_server.close()
        await backend_server.wait_closed()

    asyncio.run(asyncio.wait_for(_async_test(), timeout=5.0))

def test_telemetry_integration():
    telem = PostTelemetry()
    telem.record_frame(512, 1.0)
    telem.record_frame(1024, 0.98)
    metrics = telem.get_metrics()
    
    assert metrics["frames_processed"] == 2
    assert metrics["bytes_transmitted"] == 1536
    assert metrics["handshake_latency_ms"] == 0.0
    assert metrics["somatic_health"] == "OPTIMAL"

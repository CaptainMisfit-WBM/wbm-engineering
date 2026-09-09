"""
Process-Ontological Secure Transport (POST) Cryptographic Engine
Implements Hilbert's 6th Problem non-Hermitian phase attractor state evolution,
0-RTT dynamic key rotation, and phase coherence verification.
"""

import hmac
import hashlib
import os
import struct
import math
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

POST_MAGIC = b"POST"
POST_VERSION = 1
HEADER_STRUCT_FMT = ">4sBBHQQ32sI32s"  # 120 bytes header length
HEADER_SIZE = struct.calcsize(HEADER_STRUCT_FMT)

class PhaseAttractor:
    """
    12-Dimensional Non-Hermitian Phase Attractor State Engine.
    Evolves complex state vector |ψ(t)⟩ under H_eff = H0 - i*Γ.
    """
    def __init__(self, seed: Optional[bytes] = None):
        if seed is None:
            seed = os.urandom(32)
        self.seed = seed
        self._init_state(seed)
        self.seq = 0

    def _init_state(self, seed: bytes):
        # Generate 12 complex components from seed
        h = hashlib.sha512(seed).digest()
        self.state = []
        for i in range(12):
            re = struct.unpack(">f", h[i*2 : i*2+4])[0]
            im = struct.unpack(">f", h[24 + i*2 : 24 + i*2+4])[0]
            self.state.append(complex(re, im))
        self._normalize()

    def _normalize(self):
        norm_sq = sum(abs(z)**2 for z in self.state)
        if norm_sq < 1e-12:
            self.state = [complex(1.0 / math.sqrt(12), 0.0)] * 12
            return
        norm = math.sqrt(norm_sq)
        self.state = [z / norm for z in self.state]

    def evolve(self, dt: float = 0.05):
        """
        Evolves state vector |ψ(t)⟩ under non-Hermitian phase rotation and absorptive boundary flux.
        """
        new_state = []
        for idx, z in enumerate(self.state):
            omega = 1.5 + idx * 0.73  # Non-commensurate rotation frequencies
            gamma = 0.05 * (idx + 1)  # Differential absorptive dissipation
            
            decay = math.exp(-gamma * dt)
            phase = complex(math.cos(-omega * dt), math.sin(-omega * dt))
            perturb = complex(math.sin(idx + self.seq + 1.0), math.cos(idx + self.seq + 1.0)) * 0.1
            new_z = (z * decay * phase) + perturb
            new_state.append(new_z)
            
        self.state = new_state
        self._normalize()
        self.seq += 1

    def compute_digest(self) -> bytes:
        """
        Computes 256-bit SHA-256 Phase Digest of current state.
        """
        raw = bytearray()
        for z in self.state:
            raw.extend(struct.pack(">dd", z.real, z.imag))
        return hashlib.sha256(raw).digest()

    def derive_key(self, info: bytes = b"POST_PHASE_KEY") -> bytes:
        """
        Derives 32-byte (256-bit) AES-GCM symmetric key using HKDF-SHA256 from current state.
        """
        digest = self.compute_digest()
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.seed,
            info=info,
        )
        return hkdf.derive(digest)

    def check_coherence(self, remote_digest: bytes) -> float:
        """
        Computes reciprocal phase coherence metric C_AB between local state digest and remote digest.
        Returns float in [0.0, 1.0].
        """
        local_digest = self.compute_digest()
        if local_digest == remote_digest:
            return 1.0
        
        # Bitwise similarity score approximation for phase coherence
        matching_bits = sum(bin(b1 ^ b2).count('0') for b1, b2 in zip(local_digest, remote_digest))
        total_bits = len(local_digest) * 8
        coherence = (matching_bits / total_bits)
        return coherence

    def inject_mitm_perturbation(self):
        """
        Simulates an unauthorized non-unitary perturbation (MITM attack).
        Randomizes phase angles non-uniformly, destroying reciprocal coherence.
        """
        perturbed = []
        for idx, z in enumerate(self.state):
            phase_shift = complex(math.sin(idx * 3.7 + 1.5), math.cos(idx * 2.1 + 0.8))
            perturbed.append(z * phase_shift * (0.1 + 0.3 * idx))
        self.state = perturbed
        self._normalize()


import zlib

FLAG_COMPRESSED = 0x10

class PostCryptoEngine:
    """
    POST Crypto Frame Encapsulator & Decapsulator.
    Implements 0-RTT hydrodynamic encryption, non-Hermitian phase verification, and zlib payload compression.
    """
    def __init__(self, attractor: Optional[PhaseAttractor] = None, seed: Optional[bytes] = None):
        if attractor is not None:
            self.attractor = attractor
        else:
            self.attractor = PhaseAttractor(seed=seed)
            
    def encrypt_frame(
        self, payload: bytes, stream_id: int, seq_num: int, flags: int = 0, compress: bool = True
    ) -> bytes:
        """
        Encapsulates plain payload into a POST 1.0 encrypted transport frame with optional zlib compression.
        """
        if compress and len(payload) > 16:
            compressed_payload = zlib.compress(payload, level=6)
            if len(compressed_payload) < len(payload):
                payload = compressed_payload
                flags |= FLAG_COMPRESSED

        phase_digest = self.attractor.compute_digest()
        key = self.attractor.derive_key()
        aesgcm = AESGCM(key)
        
        # 12-byte nonce derived from seq_num
        nonce = struct.pack(">Q4x", seq_num)
        
        # Encrypt payload
        ciphertext = aesgcm.encrypt(nonce, payload, None)
        payload_len = len(ciphertext)
        
        # Compute HMAC tag over header fields
        header_pre = struct.pack(
            ">4sBBHQQ32sI",
            POST_MAGIC,
            POST_VERSION,
            flags,
            0,  # reserved
            stream_id,
            seq_num,
            phase_digest,
            payload_len,
        )
        hmac_tag = hmac.new(key, header_pre + ciphertext, hashlib.sha256).digest()
        
        full_header = struct.pack(
            HEADER_STRUCT_FMT,
            POST_MAGIC,
            POST_VERSION,
            flags,
            0,
            stream_id,
            seq_num,
            phase_digest,
            payload_len,
            hmac_tag,
        )
        
        # Evolve state for next packet
        self.attractor.evolve()
        
        return full_header + ciphertext

    def decrypt_frame(
        self, frame_bytes: bytes, min_coherence: float = 0.90
    ) -> Tuple[bytes, int, int, int]:
        """
        Decapsulates and verifies POST frame bytes.
        Returns Tuple[payload, stream_id, seq_num, flags].
        Raises ValueError on verification, phase breakdown, or decryption failure.
        """
        if len(frame_bytes) < HEADER_SIZE:
            raise ValueError(f"Frame length {len(frame_bytes)} smaller than POST header size {HEADER_SIZE}")
            
        header_data = frame_bytes[:HEADER_SIZE]
        ciphertext = frame_bytes[HEADER_SIZE:]
        
        (
            magic,
            version,
            flags,
            reserved,
            stream_id,
            seq_num,
            phase_digest,
            payload_len,
            hmac_tag,
        ) = struct.unpack(HEADER_STRUCT_FMT, header_data)
        
        if magic != POST_MAGIC:
            raise ValueError(f"Invalid POST magic bytes: {magic}")
            
        if version != POST_VERSION:
            raise ValueError(f"Unsupported POST version: {version}")
            
        if len(ciphertext) != payload_len:
            raise ValueError(f"Payload length mismatch: expected {payload_len}, got {len(ciphertext)}")
            
        # Verify Phase Coherence
        coherence = self.attractor.check_coherence(phase_digest)
        if coherence < min_coherence:
            raise ValueError(
                f"Phase Coherence Breakdown! Coherence {coherence:.4f} < threshold {min_coherence:.4f}. "
                "Possible MITM tampering or frame corruption detected."
            )
            
        key = self.attractor.derive_key()
        
        # Verify HMAC tag
        header_pre = struct.pack(
            ">4sBBHQQ32sI",
            POST_MAGIC,
            POST_VERSION,
            flags,
            reserved,
            stream_id,
            seq_num,
            phase_digest,
            payload_len,
        )
        expected_hmac = hmac.new(key, header_pre + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(hmac_tag, expected_hmac):
            raise ValueError("HMAC authentication check failed!")
            
        # Decrypt payload
        nonce = struct.pack(">Q4x", seq_num)
        aesgcm = AESGCM(key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise ValueError(f"Payload decryption failed: {e}")
            
        # Decompress payload if flag set
        if flags & FLAG_COMPRESSED:
            try:
                plaintext = zlib.decompress(plaintext)
            except Exception as e:
                raise ValueError(f"Decompression failed: {e}")

        # Evolve state for next packet
        self.attractor.evolve()
        
        return plaintext, stream_id, seq_num, flags

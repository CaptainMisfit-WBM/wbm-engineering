-- POST Protocol Dedicated Telemetry & Peer Management Database Schema
-- Location: /home/captain-misfit/DataStorage/POST/database/post_telemetry.sqlite

CREATE TABLE IF NOT EXISTS post_peers (
    peer_id TEXT PRIMARY KEY,
    public_attractor_seed BLOB NOT NULL,
    latest_coherence REAL DEFAULT 1.0,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS post_sessions (
    session_id TEXT PRIMARY KEY,
    peer_id TEXT,
    stream_id INTEGER NOT NULL,
    sequence_count INTEGER DEFAULT 0,
    uncompressed_bytes INTEGER DEFAULT 0,
    wire_frame_bytes INTEGER DEFAULT 0,
    compression_ratio REAL DEFAULT 0.0,
    handshake_latency_ms REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(peer_id) REFERENCES post_peers(peer_id)
);

CREATE TABLE IF NOT EXISTS post_benchmark_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_payload_bytes INTEGER NOT NULL,
    post_frame_bytes INTEGER NOT NULL,
    net_compression_pct REAL NOT NULL,
    execution_time_ms REAL NOT NULL,
    phase_coherence REAL DEFAULT 1.0,
    somatic_health TEXT DEFAULT 'OPTIMAL'
);

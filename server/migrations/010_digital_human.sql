-- iNNOVULIS™ — proprietary technology. Copyright © 2026 iNNOVULIS™.
-- PROPOSED POSTGRES MIGRATION ONLY: existing player_profiles and
-- real_estate_parcels migrations must run first. NOT runtime-verified.
-- Virtual parcel ownership is NOT evidence of legal land title.
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS digital_human_cognition (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    associated_owner_id UUID REFERENCES player_profiles(user_id) ON DELETE SET NULL,
    associated_parcel_id INT REFERENCES real_estate_parcels(parcel_id) ON DELETE SET NULL,
    npc_name VARCHAR(100) NOT NULL,
    personality_prompt TEXT NOT NULL,
    voice_preset_id VARCHAR(50) NOT NULL DEFAULT 'alloy',
    greed_index DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (greed_index BETWEEN 0 AND 1),
    friendliness_index DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (friendliness_index BETWEEN 0 AND 1),
    patience_index DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (patience_index BETWEEN 0 AND 1),
    source TEXT NOT NULL DEFAULT 'iNNOVULIS authored game simulation',
    as_of TIMESTAMPTZ NOT NULL DEFAULT now(),
    methodology TEXT NOT NULL DEFAULT 'simulated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS digital_human_memories (
    entity_id UUID NOT NULL REFERENCES digital_human_cognition(entity_id) ON DELETE CASCADE,
    interacted_player_id UUID NOT NULL REFERENCES player_profiles(user_id) ON DELETE CASCADE,
    conversation_history JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(conversation_history) = 'array'),
    revision BIGINT NOT NULL DEFAULT 0,
    last_interaction_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_id, interacted_player_id)
);

CREATE TABLE IF NOT EXISTS digital_human_visemes (
    viseme_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id UUID NOT NULL REFERENCES digital_human_cognition(entity_id) ON DELETE CASCADE,
    utterance_sha256 CHAR(64) NOT NULL,
    timeline JSONB NOT NULL CHECK (jsonb_typeof(timeline) = 'array'),
    audio_synchronized BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_id, utterance_sha256)
);

CREATE TABLE IF NOT EXISTS encrypted_comm_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES digital_human_cognition(entity_id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES player_profiles(user_id) ON DELETE CASCADE,
    key_id TEXT NOT NULL,
    nonce BYTEA NOT NULL CHECK (octet_length(nonce) = 12),
    ciphertext BYTEA NOT NULL,
    ciphertext_sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS cognitive_by_parcel ON digital_human_cognition(associated_parcel_id);
CREATE INDEX IF NOT EXISTS encrypted_logs_by_owner ON encrypted_comm_logs(entity_id, player_id, created_at DESC);
COMMIT;

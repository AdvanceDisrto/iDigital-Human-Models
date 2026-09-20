# iNNOVULIS™ ORCHESTRA cognitive service — reference implementation

**Status: executable local reference; not production-deployed or verified in Unity.**

This directory implements SQLite-persisted NPC dialogue, a deterministic **virtual-credit** negotiation matrix, text-estimated mouth animation cues, optional third-party AI/transcription/TTS adapters, and AES-256-GCM sealed logs. The PostgreSQL design in `server/migrations/010_digital_human.sql` is a **proposed migration**, not the database used by this reference runtime. The migration depends on the separately supplied `player_profiles` and `real_estate_parcels` tables; it has not been run against a live Postgres instance.

From the repository root on Windows PowerShell:

```powershell
py -3 -m pip install -r cognitive/requirements.txt
py -3 -m compileall -q character chain cognitive tests
py -3 -W error::ResourceWarning -m unittest discover -s tests -v
# Set your own private, random local operator token; never embed it in a Unity build.
$env:ORCHESTRA_OPERATOR_TOKEN = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:ORCHESTRA_LOG_KEY_HEX = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
py -3 -m cognitive.api
```

Local health check from another terminal: `Invoke-RestMethod http://127.0.0.1:3001/api/health`. Authentication is required for all other routes. Before chat works, explicitly enroll an entity in the local SQLite store (see the `CognitiveStore.enroll` interface) and configure `OPENAI_API_KEY` for the optional external model; without it the API returns 503 rather than inventing an AI reply. An operator token protects **a local developer reference only**, not player-scoped access. Do not ship that token, the AES key, or an API key in Unity, mobile apps, repositories, or public deployments.

Routes: `/api/digital-human/chat`, `/negotiate`, `/voice-input`, `/speak`, `/api/comm/log`, and `/api/health`. Voice input accepts bounded base64 WAV; speech synthesis returns bounded base64 WAV. Neither service emits real aligned phonemes or TTS timing. The Unity `DigitalHumanVisemePlayer.cs` can display estimated cues but has not been compiled against Unity or mapped to an actual avatar. Any voice feature must disclose synthetic speech and obtain microphone consent. The external AI providers may receive conversation/audio content; use consent, retention limits, authentication, and a privacy review before real users.

Negotiation `ACCEPTED` is **only an offer decision**; `saleCompleted` is always false. No property title transfers, wallet debits, actual valuations, authenticated cadastral records, or rent payouts occur in this reference. The local encrypted-log API deliberately has no decrypt endpoint. Server-side code must authorize each player before accessing another player's records. Keep third-party dependency notices and verify patent/trademark claims separately.

Acceptance scope: automated Python syntax/tests and mocked API providers only. The presence of API adapters or authored design documents does not establish a verified live LLM, TTS/STT call, Unity build, PostGIS migration, production privacy/security certification, or deployed game. **EXISTS ≠ IMPLEMENTED ≠ DEPLOYED ≠ RUNTIME VERIFIED.**

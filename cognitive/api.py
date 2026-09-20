"""iNNOVULIS™ proprietary local cognitive API. Development-only operator token.
Do not expose to public clients: per-player authentication and access policies are pending.
"""
import base64
import hmac
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .engine import CognitiveStore


class ChatRequest(BaseModel):
    entityId: str = Field(min_length=1, max_length=100)
    playerId: str = Field(min_length=1, max_length=100)
    playerMessage: str = Field(min_length=1, max_length=2000)


class OfferRequest(BaseModel):
    entityId: str = Field(min_length=1, max_length=100)
    proposedOfferPrice: str
    attemptNumber: int = Field(default=1, ge=1, le=20)


class LogRequest(BaseModel):
    entityId: str = Field(min_length=1, max_length=100)
    playerId: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=16000)


class VoiceRequest(BaseModel):
    entityId: str = Field(min_length=1, max_length=100)
    playerId: str = Field(min_length=1, max_length=100)
    audio_blob_base64: str = Field(min_length=1, max_length=15000000)


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    voice: str = Field(default='alloy', max_length=30)


class OpenAIReply:
    def __init__(self, key: str):
        if not key:
            raise RuntimeError('OPENAI_API_KEY required for live chat')
        self.key = key

    def reply(self, system_prompt, history):
        payload = json.dumps({'model': 'gpt-4o-mini', 'messages':
            [{'role': 'system', 'content': system_prompt}, *history[-19:]],
            'max_tokens': 180}).encode()
        request = Request('https://api.openai.com/v1/chat/completions', data=payload,
            headers={'Authorization': f'Bearer {self.key}', 'Content-Type': 'application/json'}, method='POST')
        with urlopen(request, timeout=25) as response:
            return json.load(response)['choices'][0]['message']['content']


def create_app(store: CognitiveStore, token: str, provider=None, transcriber=None,
               encryption_key: bytes | None = None, synthesizer=None) -> FastAPI:
    if len(token) < 24:
        raise ValueError('ORCHESTRA_OPERATOR_TOKEN must contain at least 24 characters')
    app = FastAPI(title='ORCHESTRA cognitive reference', version='0.1.0')

    @app.middleware('http')
    async def require_operator_token(request, call_next):
        if request.url.path != '/api/health':
            if not hmac.compare_digest(request.headers.get('authorization', ''), f'Bearer {token}'):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=401, content={'detail': 'unauthorized'})
        return await call_next(request)

    def authorize(header: str | None):
        if not header or not hmac.compare_digest(header, f'Bearer {token}'):
            raise HTTPException(status_code=401, detail='unauthorized')

    @app.get('/api/health')
    def health():
        return {'ok': True, 'deploymentVerified': False, 'runtime': 'local_reference'}

    @app.post('/api/digital-human/negotiate')
    def negotiate(payload: OfferRequest, authorization: str | None = Header(default=None)):
        authorize(authorization)
        try:
            return store.negotiate(payload.entityId, payload.proposedOfferPrice, payload.attemptNumber)
        except KeyError:
            raise HTTPException(status_code=404, detail='entity_not_found')
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post('/api/digital-human/chat')
    def chat(payload: ChatRequest, authorization: str | None = Header(default=None)):
        authorize(authorization)
        if provider is None:
            raise HTTPException(status_code=503, detail='llm_not_configured')
        try:
            return store.chat(payload.entityId, payload.playerId, payload.playerMessage, provider)
        except KeyError:
            raise HTTPException(status_code=404, detail='entity_not_found')
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except RuntimeError as exc:
            if str(exc) == 'conversation_changed_retry':
                raise HTTPException(status_code=409, detail='conversation_changed_retry')
            raise HTTPException(status_code=502, detail='llm_unavailable')
        except (HTTPError, URLError, TimeoutError):
            raise HTTPException(status_code=502, detail='llm_unavailable')

    @app.post('/api/digital-human/voice-input')
    def voice(payload: VoiceRequest, authorization: str | None = Header(default=None)):
        authorize(authorization)
        if transcriber is None:
            raise HTTPException(status_code=503, detail='speech_transcriber_not_configured')
        if provider is None:
            raise HTTPException(status_code=503, detail='llm_not_configured')
        try:
            audio = base64.b64decode(payload.audio_blob_base64, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail='invalid_audio_base64') from exc
        if not audio.startswith(b'RIFF') or audio[8:12] != b'WAVE' or not 44 <= len(audio) <= 8_000_000:
            raise HTTPException(status_code=400, detail='invalid_wav')
        try:
            text = transcriber.transcribe(audio)
            if not text or len(text) > 2000:
                raise ValueError('invalid_transcription')
            return {'transcript': text, **store.chat(payload.entityId, payload.playerId, text, provider)}
        except KeyError:
            raise HTTPException(status_code=404, detail='entity_not_found')
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            raise HTTPException(status_code=502, detail='speech_pipeline_unavailable')

    @app.post('/api/digital-human/speak')
    def speak(payload: SpeechRequest, authorization: str | None = Header(default=None)):
        authorize(authorization)
        if synthesizer is None:
            raise HTTPException(status_code=503, detail='tts_not_configured')
        try:
            audio = synthesizer.synthesize(payload.text, payload.voice)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            raise HTTPException(status_code=502, detail='tts_unavailable')
        return {'format': 'wav', 'audio_blob_base64': base64.b64encode(audio).decode(),
                'audioSynchronized': False, 'syntheticVoice': True}

    @app.post('/api/comm/log')
    def log(payload: LogRequest, authorization: str | None = Header(default=None)):
        authorize(authorization)
        if encryption_key is None:
            raise HTTPException(status_code=503, detail='encryption_key_not_configured')
        try:
            return store.seal_log(payload.entityId, payload.playerId, payload.content, encryption_key)
        except KeyError:
            raise HTTPException(status_code=404, detail='entity_not_found')
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return app


def main():
    import uvicorn
    db = os.environ.get('ORCHESTRA_DB', str(Path.home() / 'orchestra-cognitive.sqlite'))
    token = os.environ.get('ORCHESTRA_OPERATOR_TOKEN', '')
    api_key = os.environ.get('OPENAI_API_KEY', '')
    provider = OpenAIReply(api_key) if api_key else None
    log_key_hex = os.environ.get('ORCHESTRA_LOG_KEY_HEX', '')
    log_key = bytes.fromhex(log_key_hex) if log_key_hex else None
    transcriber = synthesizer = None
    if api_key:
        from .speech import OpenAITranscriber, OpenAISynthesizer
        transcriber, synthesizer = OpenAITranscriber(api_key), OpenAISynthesizer(api_key)
    app = create_app(CognitiveStore(db), token, provider, transcriber, log_key, synthesizer)
    uvicorn.run(app, host='127.0.0.1', port=3001)


if __name__ == '__main__':
    main()

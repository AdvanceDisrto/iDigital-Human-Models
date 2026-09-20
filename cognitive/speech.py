"""iNNOVULIS™ proprietary speech adapters; configured API key and billing required.
TTS response does not include phoneme timing; text visemes are approximations.
"""
import json
import uuid
from urllib.request import Request, urlopen


class OpenAITranscriber:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError('API key required')
        self.api_key = api_key

    def transcribe(self, wav: bytes) -> str:
        if not wav.startswith(b'RIFF') or wav[8:12] != b'WAVE' or not 44 <= len(wav) <= 8_000_000:
            raise ValueError('invalid wav')
        boundary = '----orchestra-' + uuid.uuid4().hex

        def field(name, data, filename=None, content_type=None):
            header = (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"' +
                      (f'; filename="{filename}"' if filename else '') + '\r\n')
            if content_type:
                header += f'Content-Type: {content_type}\r\n'
            return header.encode() + b'\r\n' + data + b'\r\n'

        body = (field('model', b'gpt-4o-mini-transcribe') +
                field('file', wav, 'speech.wav', 'audio/wav') +
                f'--{boundary}--\r\n'.encode())
        request = Request('https://api.openai.com/v1/audio/transcriptions', data=body,
            headers={'Authorization': f'Bearer {self.api_key}',
                     'Content-Type': f'multipart/form-data; boundary={boundary}'}, method='POST')
        with urlopen(request, timeout=50) as response:
            text = json.load(response)['text']
        if not isinstance(text, str) or not text.strip():
            raise ValueError('empty transcription')
        return text.strip()


class OpenAISynthesizer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError('API key required')
        self.api_key = api_key

    def synthesize(self, text: str, voice='alloy') -> bytes:
        if not isinstance(text, str) or not 1 <= len(text) <= 4096:
            raise ValueError('invalid speech text')
        if voice not in {'alloy', 'ash', 'ballad', 'coral', 'echo', 'fable', 'onyx',
                         'nova', 'sage', 'shimmer', 'verse', 'marin', 'cedar'}:
            raise ValueError('unsupported voice')
        body = json.dumps({'model': 'gpt-4o-mini-tts', 'voice': voice,
                           'input': text, 'response_format': 'wav'}).encode()
        request = Request('https://api.openai.com/v1/audio/speech', data=body,
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            method='POST')
        with urlopen(request, timeout=50) as response:
            audio = response.read(8_000_001)
        if not audio.startswith(b'RIFF') or len(audio) > 8_000_000:
            raise ValueError('invalid or oversized synthesized wav')
        return audio

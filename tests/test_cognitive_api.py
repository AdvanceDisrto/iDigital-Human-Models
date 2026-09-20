"""iNNOVULIS™ proprietary API smoke tests with mocked speech and AI providers."""
import base64
import os
import tempfile
import unittest
from fastapi.testclient import TestClient
from cognitive.api import create_app
from cognitive.engine import CognitiveStore


class StubProvider:
    def reply(self, prompt, history):
        return 'Hello broker'


class StubTranscriber:
    def transcribe(self, wav):
        return 'hello there'


class StubSynthesizer:
    def synthesize(self, text, voice):
        return b'RIFF' + b'\x00' * 4 + b'WAVE' + b'\x00' * 32


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = CognitiveStore(os.path.join(self.tmp.name, 'test.db'))
        self.store.enroll('npc', 'Broker', 'Act friendly')
        self.token = 'local-operator-test-token-1234567890'
        self.client = TestClient(create_app(self.store, self.token,
            StubProvider(), StubTranscriber(), os.urandom(32), StubSynthesizer()))
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def test_health(self):
        self.assertTrue(self.client.get('/api/health').json()['ok'])

    def test_auth(self):
        self.assertEqual(self.client.post('/api/digital-human/chat', json={}).status_code, 401)

    def test_chat(self):
        response = self.client.post('/api/digital-human/chat', headers=self.headers,
            json={'entityId': 'npc', 'playerId': 'p1', 'playerMessage': 'hi'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['audioSynchronized'])

    def test_negotiation(self):
        response = self.client.post('/api/digital-human/negotiate', headers=self.headers,
            json={'entityId': 'npc', 'proposedOfferPrice': '200000'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['saleCompleted'])

    def test_voice_rejects_bad_wav(self):
        response = self.client.post('/api/digital-human/voice-input', headers=self.headers,
            json={'entityId': 'npc', 'playerId': 'p1',
                  'audio_blob_base64': base64.b64encode(b'bad').decode()})
        self.assertEqual(response.status_code, 400)

    def test_voice_mock(self):
        wav = b'RIFF' + b'\x00' * 4 + b'WAVE' + b'\x00' * 32
        response = self.client.post('/api/digital-human/voice-input', headers=self.headers,
            json={'entityId': 'npc', 'playerId': 'p1',
                  'audio_blob_base64': base64.b64encode(wav).decode()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['transcript'], 'hello there')

    def test_tts_mock(self):
        response = self.client.post('/api/digital-human/speak', headers=self.headers,
            json={'text': 'Hello', 'voice': 'alloy'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(base64.b64decode(response.json()['audio_blob_base64']).startswith(b'RIFF'))
        self.assertFalse(response.json()['audioSynchronized'])

    def test_log_sealed_no_decrypt_endpoint(self):
        response = self.client.post('/api/comm/log', headers=self.headers,
            json={'entityId': 'npc', 'playerId': 'p1', 'content': 'private'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('private', response.text)
        self.assertEqual(self.client.post('/api/comm/unseal', headers=self.headers).status_code, 404)


if __name__ == '__main__':
    unittest.main()

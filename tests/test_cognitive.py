"""iNNOVULIS™ proprietary local cognitive smoke tests; no live AI required."""
import os
import tempfile
import unittest
from cognitive.engine import CognitiveStore, decide_offer, viseme_cues


class StubProvider:
    def reply(self, system_prompt, history):
        return f"Hello {history[-1]['content']}"


class FailProvider:
    def reply(self, system_prompt, history):
        raise RuntimeError('provider down')


class TestCognitive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, 'state.sqlite')
        self.db = CognitiveStore(self.path)
        self.db.enroll('npc-1', 'Broker', 'Friendly simulated agent', '100000', .6, .5, .7)

    def tearDown(self):
        self.tmp.cleanup()

    def test_negotiation_no_transfer(self):
        result = self.db.negotiate('npc-1', '200000')
        self.assertEqual(result['decision'], 'ACCEPTED')
        self.assertFalse(result['saleCompleted'])

    def test_counter_not_below_bid(self):
        result = self.db.negotiate('npc-1', '95000')
        self.assertEqual(result['decision'], 'COUNTER_OFFER')
        self.assertGreaterEqual(float(result['counterOffer']), 95000)

    def test_bad_prices(self):
        for price in ('NaN', '-1', 'Infinity', True, 0):
            with self.subTest(price=price), self.assertRaises(ValueError):
                decide_offer('100000', price, .5, .5, .5)

    def test_chat_and_restart(self):
        answer = self.db.chat('npc-1', 'player-1', 'offer', StubProvider())
        self.assertEqual(answer['replyText'], 'Hello offer')
        self.assertFalse(answer['audioSynchronized'])
        restarted = CognitiveStore(self.path)
        with restarted._connect() as sql:
            history = sql.execute('SELECT history FROM conversations').fetchone()[0]
        self.assertIn('Hello offer', history)

    def test_failure_does_not_store_message(self):
        with self.assertRaises(RuntimeError):
            self.db.chat('npc-1', 'player-1', 'offer', FailProvider())
        with self.db._connect() as sql:
            self.assertEqual(sql.execute('SELECT COUNT(*) FROM conversations').fetchone()[0], 0)

    def test_viseme_timing_and_th(self):
        timeline = viseme_cues('The boat.')
        self.assertEqual(timeline[0]['visemeId'], 8)
        self.assertEqual(sorted(e['time'] for e in timeline), [e['time'] for e in timeline])

    def test_encrypted_log_roundtrip_and_access(self):
        key = os.urandom(32)
        sealed = self.db.seal_log('npc-1', 'player-1', 'private words', key)
        self.assertEqual(self.db.unseal_log(sealed['logId'], 'npc-1', 'player-1', key), 'private words')
        with self.assertRaises(KeyError):
            self.db.unseal_log(sealed['logId'], 'npc-1', 'other-player', key)
        with self.assertRaises(Exception):
            self.db.unseal_log(sealed['logId'], 'npc-1', 'player-1', os.urandom(32))

    def test_100_negotiations(self):
        for i in range(100):
            result = self.db.negotiate('npc-1', str(80000 + i * 1000))
            self.assertIn(result['decision'], ('ACCEPTED', 'COUNTER_OFFER', 'REJECTED'))
            self.assertFalse(result['saleCompleted'])


if __name__ == '__main__':
    unittest.main()

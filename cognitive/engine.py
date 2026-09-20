"""iNNOVULIS™ proprietary cognitive reference engine.
Negotiation decisions do not transfer property; text visemes are not audio-synchronized.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import os
import sqlite3
import threading
import uuid
from typing import Protocol


def provenance(source: str = 'iNNOVULIS authored game simulation') -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {'source': source, 'as_of': now, 'methodology': 'simulated', 'retrieved_at': now}


def viseme_cues(text: str, rate: float = 1.0) -> list[dict]:
    """Text-estimated mouth cues, not phoneme alignment to synthesized audio."""
    if not isinstance(text, str) or len(text) > 8000 or not 0.5 <= rate <= 2.0:
        raise ValueError('invalid text or speaking rate')
    mapping = {'a': 1, 'e': 2, 'i': 3, 'y': 3, 'o': 4, 'u': 5,
               'b': 6, 'm': 6, 'p': 6, 'f': 7, 'v': 7, 'l': 9, 'w': 10, 'q': 10}
    events, t, i = [], 0.0, 0
    lower = text.lower()
    while i < len(lower):
        ch = lower[i]
        if ch.isspace():
            t += 0.11 / rate
        elif ch in '.!?':
            t += 0.22 / rate
        elif ch in ',;:':
            t += 0.066 / rate
        else:
            if lower[i:i + 2] == 'th':
                vid = 8
                i += 1
            else:
                vid = mapping.get(ch, 0)
            if vid:
                events.append({'time': round(t, 3), 'visemeId': vid, 'weight': 1.0})
            t += (0.062 if vid else 0.031) / rate
        i += 1
    return events


def _money(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError('price must be numeric')
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid price') from exc
    if not amount.is_finite() or amount <= 0 or amount > Decimal('1000000000000'):
        raise ValueError('invalid price range')
    return amount.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def decide_offer(market_value: object, offer: object, greed: float,
                 friendliness: float, patience: float, attempt: int = 1) -> dict:
    """Deterministic virtual-game negotiation; ACCEPTED is not a completed sale."""
    base, bid = _money(market_value), _money(offer)
    traits = (greed, friendliness, patience)
    if any(not isinstance(t, (int, float)) or isinstance(t, bool) or not 0 <= t <= 1 for t in traits):
        raise ValueError('traits must be within [0,1]')
    if type(attempt) is not int or not 1 <= attempt <= 20:
        raise ValueError('invalid attempt')
    reserve = base * (Decimal(1) + Decimal(str(greed)) * Decimal('.4') - Decimal(str(friendliness)) * Decimal('.15'))
    floor = base * Decimal('.8')
    if bid >= reserve:
        decision, counter = 'ACCEPTED', None
    elif bid >= floor:
        decision = 'COUNTER_OFFER'
        counter = max(bid, floor, reserve * (Decimal(1) - Decimal(str(patience)) *
                      Decimal('.015') * Decimal(attempt - 1)))
        counter = counter.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    else:
        decision, counter = 'REJECTED', None
    return {'decision': decision, 'counterOffer': str(counter) if counter is not None else None,
            'acceptedOffer': str(bid) if decision == 'ACCEPTED' else None,
            'saleCompleted': False, 'currency': 'VIRTUAL_CREDITS', **provenance()}


class ReplyProvider(Protocol):
    def reply(self, system_prompt: str, history: list[dict]) -> str: ...


class CognitiveStore:
    """SQLite-backed reference store. Backend authentication must be enforced separately."""
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        with self._connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS humans (
                  id TEXT PRIMARY KEY, npc_name TEXT NOT NULL, prompt TEXT NOT NULL,
                  market_value TEXT NOT NULL, greed REAL NOT NULL CHECK(greed BETWEEN 0 AND 1),
                  friendliness REAL NOT NULL CHECK(friendliness BETWEEN 0 AND 1),
                  patience REAL NOT NULL CHECK(patience BETWEEN 0 AND 1));
                CREATE TABLE IF NOT EXISTS conversations (
                  entity_id TEXT NOT NULL, player_id TEXT NOT NULL,
                  history TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY(entity_id,player_id), FOREIGN KEY(entity_id) REFERENCES humans(id));
                CREATE TABLE IF NOT EXISTS sealed_logs (
                  id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, player_id TEXT NOT NULL,
                  key_id TEXT NOT NULL, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
                  created_at TEXT NOT NULL, FOREIGN KEY(entity_id) REFERENCES humans(id));
            ''')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.execute('PRAGMA foreign_keys=ON')
            yield db
        finally:
            db.close()

    def enroll(self, entity_id: str, name: str, prompt: str, market_value='100000',
               greed=.5, friendliness=.5, patience=.5):
        if not entity_id or not name or not prompt or len(prompt) > 4000:
            raise ValueError('missing or invalid identity')
        _money(market_value)
        decide_offer(market_value, market_value, greed, friendliness, patience)
        with self._lock, self._connect() as db:
            db.execute('INSERT INTO humans VALUES (?,?,?,?,?,?,?)',
                       (entity_id, name, prompt, str(market_value), greed, friendliness, patience))
            db.commit()

    def get_human(self, entity_id: str):
        with self._connect() as db:
            row = db.execute('SELECT id,npc_name,prompt,market_value,greed,friendliness,patience FROM humans WHERE id=?',
                             (entity_id,)).fetchone()
        return dict(zip(('id','npc_name','prompt','market_value','greed','friendliness','patience'),row)) if row else None

    def negotiate(self, entity_id: str, offer: object, attempt: int = 1):
        npc = self.get_human(entity_id)
        if npc is None:
            raise KeyError('entity_not_found')
        return {'entityId': entity_id, **decide_offer(npc['market_value'], offer,
            npc['greed'], npc['friendliness'], npc['patience'], attempt)}

    def chat(self, entity_id: str, player_id: str, player_message: str, provider: ReplyProvider):
        if not player_id or not isinstance(player_message, str) or not 1 <= len(player_message) <= 2000:
            raise ValueError('invalid message')
        npc = self.get_human(entity_id)
        if npc is None:
            raise KeyError('entity_not_found')
        with self._connect() as db:
            row = db.execute('SELECT history,revision FROM conversations WHERE entity_id=? AND player_id=?',
                             (entity_id, player_id)).fetchone()
        history, revision = (json.loads(row[0]), row[1]) if row else ([], 0)
        request_history = history[-18:] + [{'role': 'user', 'content': player_message}]
        # No database transaction remains open during an external provider call.
        answer = provider.reply(npc['prompt'], request_history)
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 4000:
            raise ValueError('invalid provider response')
        updated = (history + [{'role': 'user', 'content': player_message},
                             {'role': 'assistant', 'content': answer}])[-40:]
        with self._lock, self._connect() as db:
            if row:
                result = db.execute('UPDATE conversations SET history=?,revision=revision+1 WHERE entity_id=? AND player_id=? AND revision=?',
                                    (json.dumps(updated), entity_id, player_id, revision))
                if result.rowcount != 1:
                    raise RuntimeError('conversation_changed_retry')
            else:
                db.execute('INSERT INTO conversations(entity_id,player_id,history) VALUES (?,?,?)',
                           (entity_id, player_id, json.dumps(updated)))
            db.commit()
        return {'success': True, 'npcName': npc['npc_name'], 'replyText': answer,
                'visemeTimeline': viseme_cues(answer), 'audioSynchronized': False, **provenance()}

    def seal_log(self, entity_id: str, player_id: str, text: str, key: bytes, key_id='local-v1'):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if len(key) != 32 or not text or len(text) > 16000:
            raise ValueError('invalid key or log text')
        if not self.get_human(entity_id):
            raise KeyError('entity_not_found')
        log_id, nonce = str(uuid.uuid4()), os.urandom(12)
        aad = f'{entity_id}|{player_id}|{log_id}|{key_id}'.encode()
        ciphertext = AESGCM(key).encrypt(nonce, text.encode(), aad)
        with self._lock, self._connect() as db:
            db.execute('INSERT INTO sealed_logs VALUES (?,?,?,?,?,?,?)',
                       (log_id, entity_id, player_id, key_id, nonce, ciphertext,
                        datetime.now(timezone.utc).isoformat()))
            db.commit()
        return {'logId': log_id, 'keyId': key_id, 'sha256': hashlib.sha256(ciphertext).hexdigest()}

    def unseal_log(self, log_id: str, entity_id: str, player_id: str, key: bytes) -> str:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        with self._connect() as db:
            row = db.execute('SELECT key_id,nonce,ciphertext FROM sealed_logs WHERE id=? AND entity_id=? AND player_id=?',
                             (log_id, entity_id, player_id)).fetchone()
        if row is None:
            raise KeyError('log_not_found')
        key_id, nonce, ciphertext = row
        aad = f'{entity_id}|{player_id}|{log_id}|{key_id}'.encode()
        return AESGCM(key).decrypt(nonce, ciphertext, aad).decode()

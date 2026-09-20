"""In-memory SHA-256 receipt chain. Not an external blockchain or durable store."""
from dataclasses import dataclass
import hashlib
import json
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Receipt:
    id: str
    action: str
    data: dict
    timestamp: float
    prev_hash: str
    hash: str


class ReceiptChain:
    GENESIS = "0" * 64

    def __init__(self):
        self.chain = []
        self.append("CHAIN_INITIALIZED", {"version": 1}, timestamp=0.0)

    def append(self, action, data, timestamp=None):
        # Snapshot caller-owned dictionaries to avoid accidental retroactive edits.
        snapshot = json.loads(json.dumps(data, sort_keys=True, allow_nan=False))
        ts = time.time() if timestamp is None else timestamp
        previous = self.chain[-1].hash if self.chain else self.GENESIS
        identifier = f"rcp_{len(self.chain):012d}"
        payload = {"id": identifier, "action": action, "data": snapshot,
                   "timestamp": ts, "prev_hash": previous}
        receipt = Receipt(**payload, hash=digest(payload))
        self.chain.append(receipt)
        return receipt

    def verify(self):
        previous = self.GENESIS
        for index, receipt in enumerate(self.chain):
            payload = {"id": receipt.id, "action": receipt.action,
                       "data": receipt.data, "timestamp": receipt.timestamp,
                       "prev_hash": receipt.prev_hash}
            if receipt.prev_hash != previous or receipt.hash != digest(payload):
                return {"valid": False, "broken_at": index}
            previous = receipt.hash
        return {"valid": True, "length": len(self.chain), "merkle_root": self.merkle_root()}

    def merkle_root(self):
        level = [r.hash for r in self.chain]
        if not level:
            return self.GENESIS
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [hashlib.sha256(bytes.fromhex(level[i]) + bytes.fromhex(level[i + 1])).hexdigest()
                     for i in range(0, len(level), 2)]
        return level[0]

    def proof(self, index):
        if not 0 <= index < len(self.chain):
            raise IndexError(index)
        level = [r.hash for r in self.chain]
        proof = []
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            sibling = index ^ 1
            proof.append({"side": "right" if index % 2 == 0 else "left", "hash": level[sibling]})
            index //= 2
            level = [hashlib.sha256(bytes.fromhex(level[i]) + bytes.fromhex(level[i + 1])).hexdigest()
                     for i in range(0, len(level), 2)]
        return proof


def verify_proof(leaf, proof, root):
    try:
        current = bytes.fromhex(leaf)
        for step in proof:
            sibling = bytes.fromhex(step["hash"])
            if step["side"] == "right":
                current = hashlib.sha256(current + sibling).digest()
            elif step["side"] == "left":
                current = hashlib.sha256(sibling + current).digest()
            else:
                return False
        return current.hex() == root
    except (ValueError, KeyError, TypeError):
        return False

"""Versioned, bounded avatar configuration; no mesh or personal location is stored."""
from dataclasses import dataclass, field
import json
import math
import re
import uuid

STYLES = frozenset({'realistic', 'stylized', 'voxel'})
FRAMEWORKS = frozenset({'uma', 'metahuman', 'vrm'})
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')

@dataclass
class CharacterProfile:
    user_id: str
    style: str
    framework: str
    height: float = 1.0
    weight: float = 1.0
    muscle: float = 0.5
    skin_hex: str = '#c8a17a'
    hair_id: int | None = None
    shirt_id: int | None = None
    pants_id: int | None = None
    shoes_id: int | None = None
    accessory_ids: list[int] = field(default_factory=list)

    def __post_init__(self):
        self.user_id = str(uuid.UUID(self.user_id))
        if self.style not in STYLES or self.framework not in FRAMEWORKS:
            raise ValueError('unsupported style or framework')
        for name, lower, upper in (('height', .5, 1.5), ('weight', .5, 1.5), ('muscle', 0, 1)):
            value = getattr(self, name)
            if not isinstance(value, (float, int)) or not math.isfinite(value) or not lower <= value <= upper:
                raise ValueError(f'invalid {name}')
        if not HEX.fullmatch(self.skin_hex):
            raise ValueError('invalid skin color')
        for item in (self.hair_id, self.shirt_id, self.pants_id, self.shoes_id, *self.accessory_ids):
            if item is not None and (type(item) is not int or item <= 0):
                raise ValueError('asset IDs must be positive integers')
        if len(self.accessory_ids) > 16 or len(set(self.accessory_ids)) != len(self.accessory_ids):
            raise ValueError('invalid accessories')


def encode(profile: CharacterProfile) -> str:
    """JSON v2 preserves numeric values exactly (unlike the lossy 3-decimal v1 draft)."""
    from dataclasses import asdict
    return json.dumps({'version': 2, 'profile': asdict(profile)}, separators=(',', ':'), sort_keys=True, allow_nan=False)


def decode(payload: str) -> CharacterProfile:
    if not isinstance(payload, str) or len(payload.encode('utf-8')) > 4096:
        raise ValueError('invalid profile size')
    obj = json.loads(payload)
    if not isinstance(obj, dict) or obj.get('version') != 2 or not isinstance(obj.get('profile'), dict):
        raise ValueError('unsupported profile version')
    expected = set(CharacterProfile.__dataclass_fields__)
    if set(obj['profile']) != expected:
        raise ValueError('unexpected or missing profile fields')
    return CharacterProfile(**obj['profile'])

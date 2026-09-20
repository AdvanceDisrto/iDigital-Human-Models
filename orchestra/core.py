"""ORCHESTRA reference routing; not a live-platform integration."""
from dataclasses import dataclass
from uuid import uuid4

TIERS = ('native', 'sdk', 'mod', 'bridge', 'chat', 'overlay', 'research')

@dataclass(frozen=True)
class Platform:
    name: str
    tier: str
    integration_path: str | None
    evidence: str | None = None

@dataclass
class Session:
    id: str
    twinion_id: str
    platform: str
    active: bool = True

class Orchestra:
    def __init__(self, chain):
        self.chain = chain
        self.platforms = {}
        self.sessions = {}

    def register_platform(self, platform):
        if platform.tier not in TIERS:
            raise ValueError('unknown tier')
        if platform.tier != 'research' and not (platform.integration_path and platform.evidence):
            raise ValueError('integration path and evidence required')
        self.platforms[platform.name] = platform
        self.chain.append('PLATFORM_CLASSIFIED', {'platform': platform.name, 'tier': platform.tier})

    def can_enter(self, name):
        p = self.platforms.get(name)
        return (bool(p and p.tier != 'research' and p.integration_path and p.evidence), p)

    def enter(self, twinion_id, platform):
        ok, p = self.can_enter(platform)
        if not ok:
            self.chain.append('ORCHESTRA_SESSION_DENIED', {'twinion': twinion_id, 'platform': platform})
            raise PermissionError('unverified integration or research tier')
        s = Session('ses_' + uuid4().hex, twinion_id, platform)
        self.sessions[s.id] = s
        self.chain.append('ORCHESTRA_SESSION_START', {'session': s.id, 'twinion': twinion_id, 'platform': platform, 'tier': p.tier})
        return s

    def leave(self, session_id):
        s = self.sessions[session_id]
        if not s.active:
            raise ValueError('session already closed')
        s.active = False
        self.chain.append('ORCHESTRA_SESSION_END', {'session': s.id})
        return {'session': s.id, 'events': []}

"""iNNOVULIS™ local-only game fixture. Run manually to enroll a simulated NPC.

No property title, real-world valuation, or external platform identity is asserted.
"""
import os
import sqlite3
from pathlib import Path
from .engine import CognitiveStore


def main():
    path = os.environ.get('ORCHESTRA_DB', str(Path.home() / 'orchestra-cognitive.sqlite'))
    store = CognitiveStore(path)
    try:
        store.enroll('demo-broker', 'Demo Broker',
                     'You are a fictional virtual-property broker. Make no claims of real land ownership.',
                     market_value='100000', greed=.6, friendliness=.6, patience=.5)
        print('Created fictional local NPC: demo-broker')
    except sqlite3.IntegrityError:
        print('Fictional local NPC already exists: demo-broker')
    print('SQLite database:', path)


if __name__ == '__main__':
    main()

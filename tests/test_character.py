import unittest
import uuid
from character.profile_codec import CharacterProfile, encode, decode
from character.master_rig import MASTER_RIG, validate_rig

class CharacterTests(unittest.TestCase):
    def profile(self):
        return CharacterProfile(user_id=str(uuid.uuid4()), style='stylized', framework='vrm', height=1.234567, accessory_ids=[4, 7])

    def test_lossless_roundtrip(self):
        original = self.profile()
        self.assertEqual(decode(encode(original)), original)

    def test_reject_nan(self):
        p = self.profile()
        p.height = float('nan')
        with self.assertRaises(ValueError):
            decode(encode(p))

    def test_reject_invalid_assets(self):
        with self.assertRaises(ValueError):
            CharacterProfile(user_id=str(uuid.uuid4()), style='voxel', framework='vrm', shirt_id=-1)

    def test_rig_valid(self):
        parents = {b.name: b.parent for b in MASTER_RIG}
        self.assertEqual(validate_rig(parents, {name: name for name in parents}), [])

    def test_rig_missing(self):
        parents = {b.name: b.parent for b in MASTER_RIG if b.name != 'Head'}
        self.assertTrue(any('Head' in error for error in validate_rig(parents, {name: name for name in parents})))

if __name__ == '__main__':
    unittest.main()

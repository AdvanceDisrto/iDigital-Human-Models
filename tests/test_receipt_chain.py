import unittest
from chain.receipt_engine import ReceiptChain, verify_proof


class ReceiptChainTests(unittest.TestCase):
    def test_chain_and_proofs(self):
        chain = ReceiptChain()
        for n in range(5):
            chain.append("TEST", {"n": n})
        result = chain.verify()
        self.assertTrue(result["valid"])
        self.assertEqual(result["length"], 6)
        for index, receipt in enumerate(chain.chain):
            self.assertTrue(verify_proof(receipt.hash, chain.proof(index), result["merkle_root"]))

    def test_tamper_detected(self):
        chain = ReceiptChain()
        chain.append("TEST", {"n": 1})
        chain.chain[1].data["n"] = 999
        self.assertFalse(chain.verify()["valid"])

    def test_input_is_snapshotted(self):
        chain = ReceiptChain()
        original = {"nested": {"n": 1}}
        chain.append("TEST", original)
        original["nested"]["n"] = 999
        self.assertTrue(chain.verify()["valid"])

    def test_bad_proof_rejected(self):
        chain = ReceiptChain()
        chain.append("TEST", {})
        proof = chain.proof(1)
        self.assertFalse(verify_proof("f" * 64, proof, chain.merkle_root()))
        with self.assertRaises(IndexError):
            chain.proof(100)


if __name__ == "__main__":
    unittest.main()

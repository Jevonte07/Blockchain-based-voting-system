import hashlib
import json
from time import time


class Blockchain:

    def __init__(self):
        self.chain = []
        self.pending_votes = []

        # Genesis block
        self.create_block(previous_hash="0", nonce=1)

    # ---------------- CREATE BLOCK ----------------
    def create_block(self, previous_hash, nonce):

        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "votes": self.pending_votes,
            "vote_count": len(self.pending_votes),
            "previous_hash": previous_hash,
            "nonce": nonce
        }

        self.pending_votes = []
        self.chain.append(block)

        return block

    # ---------------- ADD VOTE ----------------
    def add_vote(self, voter_id, candidate):

        # Privacy hash voter ID
        hidden_voter = hashlib.sha256(voter_id.encode()).hexdigest()

        vote = {
            "voter_hash": hidden_voter,
            "candidate": candidate
        }

        self.pending_votes.append(vote)

    # ---------------- HASH BLOCK ----------------
    def hash(self, block):

        encoded_block = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(encoded_block).hexdigest()

    # ---------------- LAST BLOCK ----------------
    def get_previous_block(self):
        return self.chain[-1]

    # ---------------- PROOF OF WORK ----------------
    def proof_of_work(self, previous_nonce):

        new_nonce = 1
        check = False

        while check is False:

            hash_operation = hashlib.sha256(
                str(new_nonce**2 - previous_nonce**2).encode()
            ).hexdigest()

            if hash_operation[:4] == "0000":
                check = True
            else:
                new_nonce += 1

        return new_nonce

    # ---------------- VALIDATE CHAIN ----------------
    def is_chain_valid(self):

        previous_block = self.chain[0]
        block_index = 1

        while block_index < len(self.chain):

            block = self.chain[block_index]

            # Previous hash check
            if block["previous_hash"] != self.hash(previous_block):
                return False

            # Proof check
            previous_nonce = previous_block["nonce"]
            nonce = block["nonce"]

            hash_operation = hashlib.sha256(
                str(nonce**2 - previous_nonce**2).encode()
            ).hexdigest()

            if hash_operation[:4] != "0000":
                return False

            previous_block = block
            block_index += 1

        return True
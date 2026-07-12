"""
Turns text into a 384-dim vector using a free, local embedding model.
Similar meanings -> vectors that land close together (compared later via cosine similarity).
"""
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')  # <- your line here


def embed_text(text: str) -> list[float]:
    """Returns a 384-dim embedding vector for the given text."""
    raw_vector = model.encode(text)
    return raw_vector.tolist()


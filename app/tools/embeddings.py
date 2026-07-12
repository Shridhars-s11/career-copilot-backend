"""
Turns text into a 384-dim vector using fastembed (ONNX-based, no PyTorch) --
lightweight enough to run on Render's free tier, unlike sentence-transformers.
"""
from fastembed import TextEmbedding

model = TextEmbedding()  # defaults to BAAI/bge-small-en-v1.5, 384-dim


def embed_text(text: str) -> list[float]:
    """Returns a 384-dim embedding vector for the given text."""
    result = list(model.embed([text]))
    return result[0].tolist()
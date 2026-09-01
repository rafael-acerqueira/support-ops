from __future__ import annotations

import hashlib

from supportops_api.application.documents import EmbeddingGenerator, GeneratedEmbedding


class DeterministicEmbeddingGenerator(EmbeddingGenerator):
    def __init__(
        self,
        *,
        dimensions: int = 1536,
        model: str = "supportops-deterministic-v1",
    ) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")

        self._dimensions = dimensions
        self._model = model

    async def generate(self, text: str) -> GeneratedEmbedding:
        normalized_text = " ".join(text.split())
        if not normalized_text:
            raise ValueError("Text is required to generate an embedding")

        return GeneratedEmbedding(
            values=tuple(
                _hash_to_unit_value(normalized_text, index) for index in range(self._dimensions)
            ),
            model=self._model,
            provider="deterministic",
        )


def _hash_to_unit_value(text: str, index: int) -> float:
    digest = hashlib.sha256(f"{text}:{index}".encode("utf-8")).digest()
    integer = int.from_bytes(digest[:4], byteorder="big", signed=False)
    return round((integer / 0xFFFFFFFF) * 2 - 1, 6)

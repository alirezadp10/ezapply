from __future__ import annotations

from typing import Iterable, List, Tuple

import numpy as np
import requests
from loguru import logger

from bot.schemas import FormItemSchema
from bot.settings import settings


class EmbeddingService:
    _SESSION = None
    _TIMEOUT = 60

    @staticmethod
    def get_embedding(text: str) -> List[float]:
        """
        Best-practice embedding fetch (non-agent).
        Returns [] on failure.
        """
        try:
            resp = EmbeddingService._session().post(
                settings.DEEPINFRA_EMBEDDING_API_URL,
                json={"inputs": [text]},
                timeout=EmbeddingService._TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            # DeepInfra returns {"embeddings": [[...]]} or {"embeddings": [...]}
            emb = data.get("embeddings", [])
            if isinstance(emb, list) and len(emb) == 1:
                return emb[0]  # unwrap the 2D list

            return emb

        except Exception as e:
            logger.warning(f"⚠️ Embedding fetch failed: {e}")
            return []

    @classmethod
    def _session(cls) -> requests.Session:
        if cls._SESSION is None:
            cls._SESSION = requests.Session()
            cls._SESSION.headers.update(
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                }
            )
        return cls._SESSION

    @staticmethod
    def fill_out_items(items: List["FormItemSchema"], historical: list) -> None:
        """
        Fills answers for items whose labels closely match previously stored fields,
        using cosine similarity on embeddings. Operates in-place.
        """

        # Build matrices: query (n x d) and historical (m x d), keeping row indices
        q_mat, kept_q = EmbeddingService._stack_embeddings([i.embeddings for i in items])  # (n, d)
        h_mat, kept_h = EmbeddingService._stack_embeddings([f.embedding for f in historical])  # (m, d)

        if q_mat.size == 0 or h_mat.size == 0:
            return

        # Cosine similarity matrix (n x m)
        sim = EmbeddingService._cosine_similarity_matrix(q_mat, h_mat)  # values in [-1, 1]

        # For each query, take the best historical match
        best_idx = sim.argmax(axis=1)  # (n,)
        best_scores = sim[np.arange(sim.shape[0]), best_idx]  # (n,)

        for row_i, score in enumerate(best_scores):
            if float(str(score)) >= settings.SIMILARITY_THRESHOLD:
                # Map back to original indices
                hist_j = kept_h[int(best_idx[row_i])]
                item_i = kept_q[row_i]
                items[item_i].answer = historical[hist_j].value

    @staticmethod
    def _stack_embeddings(blobs: Iterable[bytes]) -> Tuple[np.ndarray, List[int]]:
        """
        From an iterable of float32 byte blobs -> (N, D) float32 array and the list of kept indices.

        Returns:
            (array, kept_indices)
            - array: shape (N, D), dtype float32. Empty (0, 0) if no valid embeddings.
            - kept_indices: indices (into the input iterable order) of rows that were kept.
        """
        arrays: List[Tuple[int, np.ndarray]] = []
        for idx, b in enumerate(blobs):
            # Tolerate None/missing blobs
            if b is None:
                continue
            arr = np.frombuffer(b, dtype=np.float32)
            arrays.append((idx, arr))

        if not arrays:
            return np.empty((0, 0), dtype=np.float32), []

        # Validate consistent dimensionality; if not, skip mismatched rows.
        dim = arrays[0][1].shape[0]
        filtered = [(idx, a) for idx, a in arrays if a.shape[0] == dim]

        if not filtered:
            return np.empty((0, 0), dtype=np.float32), []

        kept_idx, mats = zip(*filtered)
        mat = np.vstack(mats).astype(np.float32, copy=False)
        return mat, list(kept_idx)

    @staticmethod
    def _cosine_similarity_matrix(
        a: np.ndarray, b: np.ndarray, *, out_dtype=np.float32, eps: float = 1e-12
    ) -> np.ndarray:
        """
        Pairwise cosine similarity between rows of A (n x d) and B (m x d) -> (n x m).
        - Safe for zero or near-zero vectors (treated as all-zeros => similarity 0).
        - Robust to int inputs and NaN/Inf values.
        - Numerically stable (uses float64 inside).
        """
        # Normalize inputs to float64 for stability
        a = np.asarray(a, dtype=np.float64)
        b = np.asarray(b, dtype=np.float64)

        # Replace NaN/Inf with finite numbers
        a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
        b = np.nan_to_num(b, nan=0.0, posinf=0.0, neginf=0.0)

        # Row norms (n,1) and (m,1)
        a_norms = np.linalg.norm(a, axis=1, keepdims=True)
        b_norms = np.linalg.norm(b, axis=1, keepdims=True)

        # Use np.divide with where to avoid boolean-indexing/broadcasting pitfalls.
        # Unsafe rows (norm <= eps) are set to zero rows.
        den_a = np.where(a_norms > eps, a_norms, 1.0)
        den_b = np.where(b_norms > eps, b_norms, 1.0)

        a_safe = np.divide(a, den_a, out=np.zeros_like(a), where=a_norms > eps)
        b_safe = np.divide(b, den_b, out=np.zeros_like(b), where=b_norms > eps)

        # Cosine similarity
        s = np.dot(a_safe, b_safe.T)

        # Clip to [-1, 1] (protects against tiny numerical spillover)
        np.clip(s, -1.0, 1.0, out=s)

        return s.astype(out_dtype, copy=False)

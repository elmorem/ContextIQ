"""
Embedding service for vector generation.

Provides high-level interface for generating embeddings from text using OpenAI API
with batch processing, caching, and error handling.
"""

from typing import Any

from openai import OpenAI, OpenAIError

from shared.embedding.config import EmbeddingSettings, get_embedding_settings


class EmbeddingResult:
    """Result of embedding generation operation."""

    def __init__(
        self,
        embeddings: list[list[float]],
        texts: list[str],
        model: str,
        dimensions: int,
        error: str | None = None,
    ):
        """
        Initialize embedding result.

        Args:
            embeddings: List of embedding vectors
            texts: Original texts that were embedded
            model: Model used for embedding generation
            dimensions: Dimension count of embedding vectors
            error: Error message if generation failed
        """
        self.embeddings = embeddings
        self.texts = texts
        self.model = model
        self.dimensions = dimensions
        self.error = error

    @property
    def success(self) -> bool:
        """Check if embedding generation was successful."""
        return self.error is None and len(self.embeddings) > 0

    @property
    def count(self) -> int:
        """Get number of embeddings generated."""
        return len(self.embeddings)


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI.

    Handles batch processing, retry logic, and error handling for
    embedding generation operations.
    """

    def __init__(self, settings: EmbeddingSettings | None = None):
        """
        Initialize embedding service.

        Args:
            settings: Embedding settings (uses defaults if not provided)
        """
        self.settings = settings or get_embedding_settings()
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        """
        Get or create OpenAI client instance.

        Returns:
            OpenAI client instance

        Raises:
            ValueError: If API key is not configured
        """
        if self._client is None:
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")

            self._client = OpenAI(
                api_key=self.settings.openai_api_key,
                max_retries=self.settings.openai_max_retries,
                timeout=float(self.settings.openai_timeout),
            )
        return self._client

    def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with generated embedding
        """
        return self.generate_embeddings([text])

    def generate_embeddings(self, texts: list[str]) -> EmbeddingResult:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            EmbeddingResult with generated embeddings

        Raises:
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("texts cannot be empty")

        # Truncate texts that exceed max length
        truncated_texts = self._truncate_texts(texts)

        try:
            # Call OpenAI API
            response = self.client.embeddings.create(
                model=self.settings.openai_embedding_model,
                input=truncated_texts,
                dimensions=self.settings.openai_embedding_dimensions,
            )

            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]

            return EmbeddingResult(
                embeddings=embeddings,
                texts=truncated_texts,
                model=response.model,
                dimensions=self.settings.openai_embedding_dimensions,
            )

        except OpenAIError as e:
            return EmbeddingResult(
                embeddings=[],
                texts=truncated_texts,
                model=self.settings.openai_embedding_model,
                dimensions=self.settings.openai_embedding_dimensions,
                error=f"OpenAI API error: {e}",
            )
        except Exception as e:
            return EmbeddingResult(
                embeddings=[],
                texts=truncated_texts,
                model=self.settings.openai_embedding_model,
                dimensions=self.settings.openai_embedding_dimensions,
                error=f"Embedding generation failed: {e}",
            )

    def generate_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int | None = None,
    ) -> list[EmbeddingResult]:
        """
        Generate embeddings for texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Batch size (uses default if not provided)

        Returns:
            List of EmbeddingResult objects, one per batch
        """
        batch_size = batch_size or self.settings.embedding_batch_size
        results = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            result = self.generate_embeddings(batch)
            results.append(result)

        return results

    def _truncate_texts(self, texts: list[str]) -> list[str]:
        """
        Truncate texts that exceed maximum input length.

        This is a simple character-based truncation. For production,
        consider using tiktoken for accurate token counting.

        Args:
            texts: List of texts to truncate

        Returns:
            List of truncated texts
        """
        max_chars = self.settings.embedding_max_input_length * 4  # Rough estimate

        truncated = []
        for text in texts:
            if len(text) > max_chars:
                truncated.append(text[:max_chars])
            else:
                truncated.append(text)

        return truncated

    def close(self) -> None:
        """Close the OpenAI client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "EmbeddingService":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

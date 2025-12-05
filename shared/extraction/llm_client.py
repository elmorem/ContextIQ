"""
LLM client wrapper for extraction engine.

Provides a high-level interface to Claude API with retry logic,
error handling, and structured output parsing.
"""

import json
from typing import Any

from anthropic import Anthropic, AnthropicError
from anthropic.types import Message

from shared.extraction.config import ExtractionSettings, get_extraction_settings


class LLMClient:
    """
    Wrapper around Anthropic Claude API for extraction tasks.

    Provides retry logic, error handling, and structured output parsing
    for memory extraction operations.
    """

    def __init__(self, settings: ExtractionSettings | None = None):
        """
        Initialize LLM client.

        Args:
            settings: Extraction settings (uses defaults if not provided)
        """
        self.settings = settings or get_extraction_settings()
        self._client: Anthropic | None = None

    @property
    def client(self) -> Anthropic:
        """
        Get or create Anthropic client instance.

        Returns:
            Anthropic client instance

        Raises:
            ValueError: If API key is not configured
        """
        if self._client is None:
            if not self.settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")

            self._client = Anthropic(
                api_key=self.settings.anthropic_api_key,
                max_retries=self.settings.anthropic_max_retries,
                timeout=float(self.settings.anthropic_timeout),
            )
        return self._client

    def extract_structured(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Extract structured data using Claude with JSON output.

        Args:
            system_prompt: System instructions for the extraction task
            user_message: User message containing data to extract
            response_schema: Optional JSON schema for response validation

        Returns:
            Parsed JSON response from Claude

        Raises:
            AnthropicError: If API request fails
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If response doesn't match schema
        """
        try:
            # Create message with JSON mode if schema provided
            response = self.client.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=self.settings.anthropic_max_tokens,
                temperature=self.settings.anthropic_temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            # Extract text content from response
            content = self._extract_text_content(response)

            # Parse JSON response
            result = self._parse_json_response(content)

            # Validate against schema if provided
            if response_schema:
                self._validate_schema(result, response_schema)

            return result

        except AnthropicError as e:
            raise AnthropicError(f"LLM extraction failed: {e}") from e

    def generate_text(
        self,
        system_prompt: str,
        user_message: str,
    ) -> str:
        """
        Generate text completion using Claude.

        Args:
            system_prompt: System instructions for the task
            user_message: User message/prompt

        Returns:
            Text response from Claude

        Raises:
            AnthropicError: If API request fails
        """
        try:
            response = self.client.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=self.settings.anthropic_max_tokens,
                temperature=self.settings.anthropic_temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            return self._extract_text_content(response)

        except AnthropicError as e:
            raise AnthropicError(f"LLM generation failed: {e}") from e

    def _extract_text_content(self, response: Message) -> str:
        """
        Extract text content from Claude message response.

        Args:
            response: Claude message response

        Returns:
            Extracted text content

        Raises:
            ValueError: If no text content found
        """
        for block in response.content:
            if block.type == "text":
                return block.text

        raise ValueError("No text content in response")

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """
        Parse JSON from response content.

        Handles common formatting issues like markdown code blocks.

        Args:
            content: Response content string

        Returns:
            Parsed JSON object

        Raises:
            json.JSONDecodeError: If parsing fails
        """
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        if content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove trailing ```

        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Failed to parse JSON response: {e.msg}",
                e.doc,
                e.pos,
            ) from e

    def _validate_schema(
        self,
        data: dict[str, Any],
        schema: dict[str, Any],
    ) -> None:
        """
        Validate data against a simple schema.

        Args:
            data: Data to validate
            schema: Schema with required fields

        Raises:
            ValueError: If validation fails
        """
        # Simple validation: check required fields exist
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

    def close(self) -> None:
        """Close the LLM client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "LLMClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

"""
Prompt templates for memory extraction.

Provides system prompts and few-shot examples for extracting
structured memories from conversation events.
"""

from typing import Any

# System prompt for memory extraction
EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction assistant for an AI context management system called ContextIQ.

Your task is to analyze conversation events and extract factual, atomic memories about the user, their preferences, and important information they share.

## Extraction Guidelines:

1. **Atomic Facts**: Each memory should represent ONE discrete fact
2. **Factual**: Only extract information explicitly stated, not inferred
3. **User-Centric**: Focus on facts about the USER, not general knowledge
4. **Timestamped**: All memories should have temporal context when available
5. **Categorized**: Assign appropriate categories (preference, fact, goal, etc.)

## Memory Categories:

- **preference**: User's likes, dislikes, and preferences
- **fact**: Biographical or factual information about the user
- **goal**: User's objectives, aspirations, or plans
- **habit**: Recurring behaviors or routines
- **relationship**: Information about the user's relationships with people
- **professional**: Work-related information
- **location**: Geographic information about where the user lives or travels
- **temporal**: Time-related information (birthdays, anniversaries, etc.)

## Output Format:

You must respond with valid JSON in the following format:

```json
{
  "memories": [
    {
      "fact": "Atomic fact extracted from the conversation",
      "category": "preference|fact|goal|habit|relationship|professional|location|temporal",
      "confidence": 0.0-1.0,
      "source_context": "Brief context from which this was extracted"
    }
  ]
}
```

## Quality Standards:

- **High Confidence (0.8-1.0)**: Explicitly stated facts
- **Medium Confidence (0.5-0.8)**: Strongly implied facts
- **Low Confidence (0.0-0.5)**: Weakly implied (generally avoid these)

Extract ONLY memories with confidence >= 0.5 unless the user explicitly requests all extractions.

## What NOT to Extract:

- General knowledge or facts not specific to the user
- Agent responses or system information
- Temporary conversation state
- Purely conversational filler
"""

# Few-shot examples for extraction
FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "conversation": """User: I'm Mark, and I love pizza. I'm a software engineer at Google.
Agent: Nice to meet you, Mark! That's great that you work at Google.""",
        "extraction": {
            "memories": [
                {
                    "fact": "User's name is Mark",
                    "category": "fact",
                    "confidence": 1.0,
                    "source_context": "User introduced himself as Mark",
                },
                {
                    "fact": "User loves pizza",
                    "category": "preference",
                    "confidence": 1.0,
                    "source_context": "User explicitly stated he loves pizza",
                },
                {
                    "fact": "User works as a software engineer at Google",
                    "category": "professional",
                    "confidence": 1.0,
                    "source_context": "User stated his job title and employer",
                },
            ]
        },
    },
    {
        "conversation": """User: I'm planning to visit Tokyo next spring for the cherry blossoms.
Agent: That sounds wonderful! Tokyo is beautiful during cherry blossom season.""",
        "extraction": {
            "memories": [
                {
                    "fact": "User is planning to visit Tokyo in spring",
                    "category": "goal",
                    "confidence": 1.0,
                    "source_context": "User stated travel plans for Tokyo next spring",
                },
                {
                    "fact": "User is interested in seeing cherry blossoms in Tokyo",
                    "category": "preference",
                    "confidence": 0.9,
                    "source_context": "User mentioned cherry blossoms as motivation for Tokyo visit",
                },
            ]
        },
    },
    {
        "conversation": """User: My daughter just started kindergarten last week. She's really excited about it!
Agent: How wonderful! Kindergarten is such a big milestone.""",
        "extraction": {
            "memories": [
                {
                    "fact": "User has a daughter",
                    "category": "relationship",
                    "confidence": 1.0,
                    "source_context": "User mentioned 'my daughter'",
                },
                {
                    "fact": "User's daughter recently started kindergarten",
                    "category": "fact",
                    "confidence": 1.0,
                    "source_context": "User stated daughter started kindergarten last week",
                },
            ]
        },
    },
]


def build_extraction_prompt(
    conversation_events: list[dict[str, str]],
    include_few_shot: bool = True,
    max_examples: int = 3,
) -> str:
    """
    Build extraction prompt from conversation events.

    Args:
        conversation_events: List of events with 'speaker' and 'content'
        include_few_shot: Whether to include few-shot examples
        max_examples: Maximum number of few-shot examples to include

    Returns:
        Formatted user message for extraction
    """
    prompt_parts = []

    # Add few-shot examples if requested
    if include_few_shot and max_examples > 0:
        prompt_parts.append("Here are some examples of good memory extraction:\n")

        for i, example in enumerate(FEW_SHOT_EXAMPLES[:max_examples], 1):
            prompt_parts.append(f"Example {i}:")
            prompt_parts.append(f"Conversation:\n{example['conversation']}\n")
            prompt_parts.append("Extracted Memories:")
            prompt_parts.append(f"{format_extraction(example['extraction'])}\n")

        prompt_parts.append("---\n")

    # Add current conversation
    prompt_parts.append("Now, extract memories from this conversation:\n")

    for event in conversation_events:
        speaker = event.get("speaker", "Unknown")
        content = event.get("content", "")
        prompt_parts.append(f"{speaker}: {content}")

    prompt_parts.append("\nExtract all relevant memories in JSON format:")

    return "\n".join(prompt_parts)


def format_extraction(extraction: dict) -> str:
    """
    Format extraction result as pretty JSON.

    Args:
        extraction: Extraction result dictionary

    Returns:
        Formatted JSON string
    """
    import json

    return json.dumps(extraction, indent=2)


# Response schema for validation
EXTRACTION_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["memories"],
    "properties": {
        "memories": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["fact", "category", "confidence"],
                "properties": {
                    "fact": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "preference",
                            "fact",
                            "goal",
                            "habit",
                            "relationship",
                            "professional",
                            "location",
                            "temporal",
                        ],
                    },
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "source_context": {"type": "string"},
                },
            },
        }
    },
}

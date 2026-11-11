
import json
import logging
from typing import Any

from groq import AsyncGroq

from app.config.settings import settings

logger = logging.getLogger(__name__)


class ConversationLLMService:

    def __init__(self):
        self.client = (
            AsyncGroq(api_key=settings.groq_api_key)
            if settings.groq_api_key
            else None
        )
        self.model = settings.groq_llm_model

    async def analyze_conversation(
        self,
        conversation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze a reconstructed conversation using Groq.
        Returns a structured JSON analysis.
        """

        if not self.client:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        messages = conversation.get("messages", [])

        if not messages:
            raise ValueError(
                "No reconstructed messages available for analysis."
            )

        conversation_text = self._format_conversation(messages)

        system_prompt = """
You are an expert business conversation analyst.

Analyze the supplied conversation and return only valid JSON.

Rules:
1. Use only information present in the conversation.
2. Never invent names, facts, requirements, or commitments.
3. If information is unavailable, return null or an empty list.
4. Distinguish customer intent from the other participant's intent.
5. Identify objections only when explicitly expressed.
6. Recommendations must be based on the actual conversation.
7. Do not treat OCR uncertainty as confirmed information.

Return this exact JSON structure:

{
  "conversation_summary": "string",
  "customer_intent": "string or null",
  "interest_level": "high | medium | low | unknown",
  "sentiment": "positive | negative | neutral | mixed | unknown",
  "business_requirements": [],
  "key_points": [],
  "questions_asked": [],
  "objections": [],
  "decisions": [],
  "commitments": [],
  "follow_up_required": false,
  "follow_up_actions": [],
  "recommended_next_action": "string or null",
  "important_insights": []
}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": (
                            "Analyze this conversation:\n\n"
                            + conversation_text
                        ),
                    },
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
                max_completion_tokens=3000,
            )

            content = response.choices[0].message.content

            if not content:
                raise ValueError("Groq returned an empty analysis.")

            result = json.loads(content)

            self._validate_result(result)

            logger.info(
                "Conversation analysis completed using model %s",
                self.model,
            )

            return result

        except json.JSONDecodeError as exc:
            logger.exception("Groq returned invalid JSON.")
            raise ValueError(
                "LLM returned an invalid JSON response."
            ) from exc

        except Exception:
            logger.exception("Groq conversation analysis failed.")
            raise

    @staticmethod
    def _format_conversation(messages: list[dict]) -> str:
        formatted_messages = []

        for message in messages:
            sender = message.get("sender") or "Unknown"
            timestamp = message.get("timestamp") or ""
            date = message.get("date") or ""
            text = message.get("text", "")

            if not text.strip():
                continue

            formatted_messages.append(
                f"[{date} {timestamp}] {sender}: {text}"
            )

        return "\n".join(formatted_messages)

    @staticmethod
    def _validate_result(result: dict) -> None:
        required_fields = [
            "conversation_summary",
            "customer_intent",
            "interest_level",
            "sentiment",
            "business_requirements",
            "key_points",
            "questions_asked",
            "objections",
            "decisions",
            "commitments",
            "follow_up_required",
            "follow_up_actions",
            "recommended_next_action",
            "important_insights",
        ]

        if not isinstance(result, dict):
            raise ValueError("LLM analysis must be a JSON object.")

        missing_fields = [
            field for field in required_fields
            if field not in result
        ]

        if missing_fields:
            raise ValueError(
                f"LLM analysis is missing fields: {missing_fields}"
            )

        list_fields = [
            "business_requirements",
            "key_points",
            "questions_asked",
            "objections",
            "decisions",
            "commitments",
            "follow_up_actions",
            "important_insights",
        ]

        for field in list_fields:
            if not isinstance(result[field], list):
                raise ValueError(
                    f"LLM field '{field}' must be a list."
                )

        if not isinstance(result["follow_up_required"], bool):
            raise ValueError(
                "follow_up_required must be a boolean."
            )


conversation_llm_service = ConversationLLMService()

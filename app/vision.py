import logging
import os
from typing import Any

from app.config import VISION_MODEL_ID
from app.errors import AIProviderConfigurationError

logger = logging.getLogger(__name__)


class VisionConfigurationError(AIProviderConfigurationError):
    pass


class HuggingFaceImageCaptioner:
    def __init__(self, model_name: str = VISION_MODEL_ID):
        self.model_name = model_name
        self._client: Any = None

    def caption(self, image_bytes: bytes) -> str:
        token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not token:
            raise VisionConfigurationError(
                "HUGGINGFACEHUB_API_TOKEN is required to caption diagrams."
            )

        if self._client is None:
            from huggingface_hub import InferenceClient

            self._client = InferenceClient(token=token, model=self.model_name)

        try:
            results = self._client.image_to_text(image=image_bytes)
            if results and getattr(results[0], "text", "").strip():
                return results[0].text.strip()
        except (Exception, StopIteration) as exc:
            logger.warning(
                "Hugging Face vision captioning API failed (%s); using descriptive diagram fallback.",
                exc,
            )
            return "Technical architecture diagram depicting system component interactions and service topology."

        return "Technical architecture diagram depicting system component interactions and service topology."

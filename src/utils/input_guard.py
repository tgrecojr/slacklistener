"""Prompt injection detection using LLM-Guard."""

import logging

logger = logging.getLogger(__name__)


class InputGuard:
    """Screens user input for prompt injection attacks."""

    def __init__(self, threshold: float = 0.92, use_onnx: bool = True):
        from llm_guard.input_scanners import PromptInjection
        from llm_guard.input_scanners.prompt_injection import MatchType

        self._scanner = PromptInjection(
            threshold=threshold,
            match_type=MatchType.FULL,
            use_onnx=use_onnx,
        )
        # Warmup: triggers model download/load on first call
        self._scanner.scan("warmup")
        logger.info("InputGuard initialized (threshold=%.2f)", threshold)

    def scan(self, text: str) -> tuple[bool, float]:
        """
        Scan text for prompt injection.

        Returns:
            (is_safe, risk_score) -- is_safe=True if input passes
        """
        if not text or not text.strip():
            return True, 0.0

        _, is_valid, risk_score = self._scanner.scan(text)
        if not is_valid:
            logger.warning(
                "Prompt injection detected (score=%.3f): %.80s...",
                risk_score,
                text,
            )
        return is_valid, risk_score

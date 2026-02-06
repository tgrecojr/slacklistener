"""Prompt injection detection using Meta LlamaFirewall."""

import logging

logger = logging.getLogger(__name__)


class InputGuard:
    """Screens user input for prompt injection attacks."""

    def __init__(self, threshold: float = 0.9):
        from llamafirewall.scanners.promptguard_utils import PromptGuard

        self._prompt_guard = PromptGuard()
        self._threshold = threshold
        # Warmup: trigger model load + first inference
        self._prompt_guard.get_jailbreak_score("warmup")
        logger.info("InputGuard initialized (threshold=%.2f)", threshold)

    def scan(self, text: str) -> tuple[bool, float]:
        """
        Scan text for prompt injection.

        Returns:
            (is_safe, risk_score) -- is_safe=True if input passes
        """
        if not text or not text.strip():
            return True, 0.0

        risk_score = self._prompt_guard.get_jailbreak_score(text)
        is_safe = risk_score < self._threshold
        if not is_safe:
            logger.warning(
                "Prompt injection detected (score=%.3f): %.80s...",
                risk_score,
                text,
            )
        return is_safe, risk_score

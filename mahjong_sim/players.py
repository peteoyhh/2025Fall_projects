from typing import Union
import random


class NeutralPolicy:
    """
    Soft-defensive neutral player policy used for Experiment 1 tables.

    Rules:
        - If risk > threshold -> Hu immediately (avoid danger)
        - If fan >= 1 -> Hu
        - Otherwise continue_probability% chance to continue chasing higher fan
    """

    def __init__(self, seed: Union[int, None] = None, thresholds: dict = None) -> None:
        """
        Args:
            seed: Random seed for probability decisions
            thresholds: Optional dict with risk_threshold and continue_probability
        """
        self._rng = random.Random(seed)
        self.thresholds = thresholds or {
            "risk_threshold": 0.4,
            "continue_probability": 0.2
        }

    def should_hu(self, fan: Union[int, float], risk: float) -> bool:
        if risk > self.thresholds["risk_threshold"]:
            return True
        if fan >= 1:
            return True
        # continue_probability% chance to chase higher fan (i.e., continue drawing)
        return self._rng.random() >= self.thresholds["continue_probability"]


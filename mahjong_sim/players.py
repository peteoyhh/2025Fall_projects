from typing import Union
import random


class NeutralPolicy:
    """
    Balanced neutral player policy used for Experiment 1 tables.
    
    Strategy: Between DEF and AGG, similar to ValueChaser but less strict.
    - Low risk: Pursues fan >= 3 (like ValueChaser pursues fan >= 5)
    - Medium risk: Accepts fan >= 2 (more flexible than ValueChaser)
    - High risk: Accepts any valid win (fan >= 1) to avoid danger
    - Prevents winning on small fans when risk is low (unlike DEF)
    """

    def __init__(self, seed: Union[int, None] = None, thresholds: dict = None) -> None:
        """
        Args:
            seed: Random seed (None for system random, not used in experiments)
            thresholds: Optional dict with target_fan, medium_risk_threshold, and bailout_risk_threshold
        """
        self._rng = random.Random(seed)
        self.thresholds = thresholds or {
            "target_fan": 3,  # Target fan for low risk (between DEF's 1 and AGG's 5)
            "medium_risk_threshold": 0.45,  # Risk level to start accepting fan >= 2 wins
            "bailout_risk_threshold": 0.70  # Risk level to bail out and accept any win (fan >= 1)
        }

    def should_hu(self, fan: Union[int, float], risk: float) -> bool:
        target_fan = self.thresholds.get("target_fan", 3)
        medium_risk = self.thresholds.get("medium_risk_threshold", 0.45)
        bailout_risk = self.thresholds.get("bailout_risk_threshold", 0.70)
        
        # High risk: risk >= 0.70, accept fan >= 1
        if risk >= bailout_risk:
            return fan >= 1
        
        # Medium risk: 0.45 <= risk < 0.70, accept fan >= 2
        if risk >= medium_risk and risk < bailout_risk:
            return fan >= 2
        
        # Low risk: risk < 0.45, pursue target fan (fan >= 3)
        return fan >= target_fan


from typing import Union
from dataclasses import dataclass
from collections import Counter

# -----------------------------------------------------------------------------
# Legacy threshold-based strategies (kept for compatibility with existing tests)
# -----------------------------------------------------------------------------


def defensive_strategy(fan: Union[int, float], fan_min: int = 1) -> bool:
    """
    Defensive strategy: accepts any hand with fan >= fan_min.
    
    Note: fan_min should be >= 1 because Pi Hu (0 fan) is not a legal winning hand.
    
    Args:
        fan: Total fan count (including Gong bonuses)
        fan_min: Minimum fan threshold (default: 1)
    
    Returns:
        Boolean: True if strategy accepts this fan level
    """
    return fan >= fan_min


def aggressive_strategy(fan: Union[int, float], threshold: int = 3) -> bool:
    """
    Aggressive strategy: only accepts hands with fan >= threshold.
    
    Rejects low-fan hands to pursue higher-value combinations.
    
    Args:
        fan: Total fan count (including Gong bonuses)
        threshold: Minimum fan threshold (default: 3)
    
    Returns:
        Boolean: True if strategy accepts this fan level
    """
    return fan >= threshold


# -----------------------------------------------------------------------------
# Strategy interface and richer strategy implementations
# -----------------------------------------------------------------------------

@dataclass
class TableState:
    discard_pile: list
    wall_remaining: int
    turn: int
    risk: float


class BaseStrategy:
    """Interface for Mahjong decision policies."""

    name: str = "BASE"

    def should_hu(self, fan: int, risk: float, hand, fan_min: int, fan_threshold: int) -> bool:
        raise NotImplementedError

    def decide_claim(self, action: str, context: dict) -> bool:
        """
        Decide whether to claim a discard for a given action.
        action: 'hu' | 'gong' | 'pong' | 'chi'
        context includes fan, risk, table_state, hand, meld_options (for chi)
        """
        raise NotImplementedError

    def choose_discard(self, hand, table_state: TableState):
        """Return a Tile to discard."""
        raise NotImplementedError


def _tile_key(tile):
    return (tile.tile_type.value, tile.value)


def _suit_majority(hand_tiles):
    counts = Counter(t.tile_type for t in hand_tiles)
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _meld_potential_score(tile, hand_tiles, weights=None):
    """
    Minimal heuristic: pairs > near-sequences > honors.
    Lower score => worse tile to keep.
    
    Args:
        tile: Tile to evaluate
        hand_tiles: List of tiles in hand
        weights: Optional dict with scoring weights (pair_potential, sequence_potential, honor_value)
    """
    if weights is None:
        weights = {"pair_potential": 3, "sequence_potential": 0.5, "honor_value": 0.8}
    
    same = sum(1 for t in hand_tiles if t == tile)
    score = 0
    if same >= 2:
        score += weights.get("pair_potential", 3)  # pair/pong potential
    # two-sided wait potential
    for delta in (-2, -1, 1, 2):
        for t in hand_tiles:
            if t.tile_type == tile.tile_type and t.value == tile.value + delta:
                score += weights.get("sequence_potential", 0.5)
    if tile.tile_type.name in ["FENG", "JIAN"]:
        score += weights.get("honor_value", 0.8)  # small value for honors
    return score


def _safety_score(tile, discard_pile):
    """Safer if already visible in discards (fewer remaining copies)."""
    seen = sum(1 for t in discard_pile if t == tile)
    return seen  # higher is safer


class TempoDefender(BaseStrategy):
    """
    Fast and conservative strategy:
    - Wins when fan >= fan_min; tends to accept wins even at high risk.
    - Rarely claims chi/pong/gong.
    - Discards the safest tiles with lowest meld potential.
    """

    name = "DEF_TEMPO"

    def __init__(self, thresholds=None, weights=None):
        """
        Args:
            thresholds: Optional dict with strategy thresholds
            weights: Optional dict with scoring weights
        """
        self.thresholds = thresholds or {
            "high_risk_threshold": 0.5,
            "gong_risk_threshold": 0.35,
            "pong_risk_threshold": 0.5,
            "chi_risk_threshold": 0.35,
            "risk_fan_adjustment": 0.5
        }
        self.weights = weights or {
            "pair_potential": 3,
            "sequence_potential": 0.5,
            "honor_value": 0.8,
            "suit_penalty": 2,
            "safety_weight": 0.3
        }

    def should_hu(self, fan: int, risk: float, hand, fan_min: int, fan_threshold: int) -> bool:
        if fan >= fan_min:
            return True
        # High table risk -> take the win if available
        return risk >= self.thresholds["high_risk_threshold"] and fan >= fan_min - self.thresholds["risk_fan_adjustment"]

    def decide_claim(self, action: str, context: dict) -> bool:
        risk = context.get("risk", 0.0)
        fan = context.get("fan", 0)
        if action == "hu":
            return True
        if action == "gong":
            return risk < self.thresholds["gong_risk_threshold"]
        if action == "pong":
            return risk < self.thresholds["pong_risk_threshold"]
        if action == "chi":
            return risk < self.thresholds["chi_risk_threshold"]
        return False

    def choose_discard(self, hand, table_state: TableState):
        tiles = hand.tiles
        discard_pile = table_state.discard_pile
        # Score tiles: lower meld potential and higher safety -> discard first
        scored = []
        for t in tiles:
            potential = _meld_potential_score(t, tiles, self.weights)
            safety = _safety_score(t, discard_pile)
            scored.append((potential, safety, t))
        scored.sort(key=lambda x: (x[0], -x[1]))  # lowest potential, highest safety
        return scored[0][2] if scored else None


class ValueChaser(BaseStrategy):
    """
    Pursues high fan strategy:
    - Only wins when fan reaches threshold; falls back to minimum when risk is too high.
    - Willing to claim pong/gong for fan; can claim chi early.
    - Discards tiles that don't match dominant suit or have low potential first.
    """

    name = "VAL_CHASER"

    def __init__(self, target_threshold: int = 3, thresholds=None, weights=None):
        """
        Args:
            target_threshold: Minimum fan threshold for winning
            thresholds: Optional dict with strategy thresholds
            weights: Optional dict with scoring weights
        """
        self.target_threshold = target_threshold
        self.thresholds = thresholds or {
            "bailout_risk_threshold": 0.65,
            "chi_risk_threshold": 0.7,
            "chi_wall_threshold": 25
        }
        self.weights = weights or {
            "pair_potential": 3,
            "sequence_potential": 0.5,
            "honor_value": 0.8,
            "suit_penalty": 2,
            "safety_weight": 0.3
        }

    def should_hu(self, fan: int, risk: float, hand, fan_min: int, fan_threshold: int) -> bool:
        threshold = max(self.target_threshold, fan_threshold)
        if risk > self.thresholds["bailout_risk_threshold"]:
            # bail out if table is dangerous
            return fan >= fan_min
        return fan >= threshold

    def decide_claim(self, action: str, context: dict) -> bool:
        risk = context.get("risk", 0.0)
        fan = context.get("fan", 0)
        table_state: TableState = context.get("table_state")
        wall_remaining = table_state.wall_remaining if table_state else 50

        if action == "hu":
            return self.should_hu(fan, risk, None, 1, self.target_threshold)
        if action == "gong":
            return True  # extra fan
        if action == "pong":
            return True  # build pongs / all-pongs value
        if action == "chi":
            return wall_remaining > self.thresholds["chi_wall_threshold"] and risk < self.thresholds["chi_risk_threshold"]
        return False

    def choose_discard(self, hand, table_state: TableState):
        tiles = hand.tiles
        discard_pile = table_state.discard_pile
        dominant_suit = _suit_majority(tiles)

        scored = []
        for t in tiles:
            suit_penalty = 0
            if dominant_suit and t.tile_type != dominant_suit and t.tile_type.name not in ["FENG", "JIAN"]:
                suit_penalty = self.weights.get("suit_penalty", 2)  # Discard tiles that don't match dominant suit first
            potential = _meld_potential_score(t, tiles, self.weights)
            safety = _safety_score(t, discard_pile)
            keep_score = potential - suit_penalty + safety * self.weights.get("safety_weight", 0.3)
            scored.append((keep_score, t))
        scored.sort(key=lambda x: x[0])  # Discard the lowest scored
        return scored[0][1] if scored else None

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
    # Enhanced fields for richer strategy decisions
    opponent_discards_by_suit: dict = None  # Dict mapping suit -> list of discarded tiles
    total_tiles_discarded: int = 0  # Total tiles discarded by all players


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


def _hand_completion_score(hand, weights=None):
    """
    Estimate how close the hand is to a valid winning structure.
    Returns a score where higher = closer to completion.
    
    Heuristic components:
    - Number of completed melds (already formed)
    - Number of pairs (good for eyes)
    - Number of tatsu (2-tile sequences that can become chi)
    - Number of isolated tiles (bad, reduce score)
    
    Args:
        hand: Hand object
        weights: Optional dict with weights for different components
    """
    if weights is None:
        weights = {
            "completed_meld": 3.0,
            "pair": 1.5,
            "tatsu": 0.8,
            "isolated_penalty": -0.5
        }
    
    tiles = hand.tiles
    melds = hand.melds
    
    # Count completed melds (excluding pair)
    completed_melds = sum(1 for m in melds if len(m) >= 3)
    
    # Analyze hand tiles for pairs and tatsu
    tile_counts = Counter(tiles)
    pairs = 0
    tatsu = 0
    isolated = 0
    
    # Count pairs
    for tile, count in tile_counts.items():
        if count >= 2:
            pairs += 1
    
    # Count tatsu (2-tile sequences that can become chi)
    # A tatsu is two consecutive tiles of the same suit
    tiles_by_suit = {}
    for tile in tiles:
        if tile.tile_type not in tiles_by_suit:
            tiles_by_suit[tile.tile_type] = []
        tiles_by_suit[tile.tile_type].append(tile.value)
    
    for suit, values in tiles_by_suit.items():
        if suit.name in ["FENG", "JIAN"]:
            continue  # Honors don't form sequences
        sorted_values = sorted(set(values))
        for i in range(len(sorted_values) - 1):
            if sorted_values[i+1] - sorted_values[i] <= 2:  # Consecutive or one gap
                tatsu += 1
    
    # Count isolated tiles (tiles with no nearby tiles)
    for tile in tiles:
        if tile.tile_type.name in ["FENG", "JIAN"]:
            continue  # Honors are evaluated separately
        is_isolated = True
        for other_tile in tiles:
            if other_tile == tile:
                continue
            if other_tile.tile_type == tile.tile_type:
                if abs(other_tile.value - tile.value) <= 2:
                    is_isolated = False
                    break
        if is_isolated:
            isolated += 1
    
    # Calculate completion score
    score = (completed_melds * weights.get("completed_meld", 3.0) +
             pairs * weights.get("pair", 1.5) +
             tatsu * weights.get("tatsu", 0.8) +
             isolated * weights.get("isolated_penalty", -0.5))
    
    return score


def _opponent_suit_availability(discard_pile, opponent_discards_by_suit=None):
    """
    Analyze opponent discard patterns to estimate suit availability.
    Returns a dict mapping suit -> availability score (higher = more available/safer).
    
    Logic:
    - Suits frequently discarded by opponents are more available
    - Suits rarely discarded are less available (higher risk)
    """
    if opponent_discards_by_suit is None:
        # Fallback: analyze from general discard pile
        suit_counts = Counter(t.tile_type for t in discard_pile)
        total_discards = len(discard_pile)
        if total_discards == 0:
            return {}  # No data yet
        
        availability = {}
        for suit, count in suit_counts.items():
            availability[suit] = count / max(total_discards, 1)
        return availability
    
    # Use opponent-specific discard data
    availability = {}
    total_opponent_discards = sum(len(discards) for discards in opponent_discards_by_suit.values())
    
    if total_opponent_discards == 0:
        return {}
    
    for suit, discards in opponent_discards_by_suit.items():
        availability[suit] = len(discards) / max(total_opponent_discards, 1)
    
    return availability


def _evaluate_post_discard_hand(hand, tile_to_discard, weights=None):
    """
    Evaluate hand quality after discarding a specific tile.
    Returns a score where higher = better hand structure after discard.
    
    Args:
        hand: Hand object
        tile_to_discard: Tile to be discarded
        weights: Optional dict with weights
    """
    if weights is None:
        weights = {
            "isolated_reduction": 2.0,
            "structure_clarity": 1.5,
            "completion_improvement": 1.0
        }
    
    # Create a temporary hand without the tile
    # Only remove one instance if tile appears multiple times
    temp_tiles = hand.tiles.copy()
    try:
        temp_tiles.remove(tile_to_discard)
    except ValueError:
        # Tile not in hand (shouldn't happen in normal flow, but handle gracefully)
        pass
    
    if len(temp_tiles) == 0:
        return -10.0  # Bad: no tiles left
    
    # Count isolated tiles before and after
    isolated_before = 0
    isolated_after = 0
    
    for tile in hand.tiles:
        if tile.tile_type.name in ["FENG", "JIAN"]:
            continue
        is_isolated = True
        for other_tile in hand.tiles:
            if other_tile == tile:
                continue
            if other_tile.tile_type == tile.tile_type and abs(other_tile.value - tile.value) <= 2:
                is_isolated = False
                break
        if is_isolated:
            isolated_before += 1
    
    for tile in temp_tiles:
        if tile.tile_type.name in ["FENG", "JIAN"]:
            continue
        is_isolated = True
        for other_tile in temp_tiles:
            if other_tile == tile:
                continue
            if other_tile.tile_type == tile.tile_type and abs(other_tile.value - tile.value) <= 2:
                is_isolated = False
                break
        if is_isolated:
            isolated_after += 1
    
    isolated_reduction = isolated_before - isolated_after
    
    # Evaluate structure clarity (pairs and tatsu in remaining tiles)
    tile_counts = Counter(temp_tiles)
    pairs_after = sum(1 for count in tile_counts.values() if count >= 2)
    
    tiles_by_suit = {}
    for tile in temp_tiles:
        if tile.tile_type not in tiles_by_suit:
            tiles_by_suit[tile.tile_type] = []
        if tile.tile_type.name not in ["FENG", "JIAN"]:
            tiles_by_suit[tile.tile_type].append(tile.value)
    
    tatsu_after = 0
    for suit, values in tiles_by_suit.items():
        if suit.name in ["FENG", "JIAN"]:
            continue
        sorted_values = sorted(set(values))
        for i in range(len(sorted_values) - 1):
            if sorted_values[i+1] - sorted_values[i] <= 2:
                tatsu_after += 1
    
    structure_clarity = pairs_after + tatsu_after
    
    # Calculate score
    score = (isolated_reduction * weights.get("isolated_reduction", 2.0) +
             structure_clarity * weights.get("structure_clarity", 1.5))
    
    return score


def _get_dynamic_weights(base_weights, hand_completion, turn, wall_remaining, max_turns=100):
    """
    Dynamically adjust strategy weights based on hand completion and round progression.
    
    Args:
        base_weights: Base weight dictionary
        hand_completion: Hand completion score
        turn: Current turn number
        wall_remaining: Tiles remaining in wall
        max_turns: Maximum turns in a round (for normalization)
    
    Returns:
        Adjusted weights dictionary
    """
    # Normalize turn progression (0 = early game, 1 = late game)
    # Use wall_remaining as a better indicator of game progress
    # Total tiles: 136, dealt: 53 (4 players * 13 + dealer 1 extra) = 83 remaining
    # Normalize based on wall remaining (lower wall = later game)
    if wall_remaining > 0:
        # Wall starts around 83 tiles after dealing, normalize to 0-1
        wall_progress = max(0, min(1.0, (83 - wall_remaining) / 83.0))
    else:
        wall_progress = 1.0  # Wall exhausted = late game
    
    # Also consider turn number as backup
    turn_progress = min(turn / max(max_turns, 1), 1.0)
    
    # Combine both indicators (weight wall more heavily)
    combined_progress = 0.7 * wall_progress + 0.3 * turn_progress
    
    # Normalize hand completion (assume max completion ~12-15)
    # Handle negative completion scores
    completion_normalized = min(max(hand_completion / 15.0, 0.0), 1.0)
    
    # Early game: more exploration, less safety focus
    # Late game: more safety, prioritize completion
    safety_multiplier = 0.3 + (combined_progress * 0.7)  # 0.3 early -> 1.0 late
    
    # High completion: prioritize safety and completion
    # Low completion: prioritize exploration and potential
    potential_multiplier = 1.0 - (completion_normalized * 0.3)  # 1.0 low -> 0.7 high
    
    adjusted_weights = base_weights.copy()
    if "safety_weight" in adjusted_weights:
        adjusted_weights["safety_weight"] *= safety_multiplier
    if "pair_potential" in adjusted_weights:
        adjusted_weights["pair_potential"] *= potential_multiplier
    if "sequence_potential" in adjusted_weights:
        adjusted_weights["sequence_potential"] *= potential_multiplier
    
    return adjusted_weights


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
            "safety_weight": 0.3,
            "completed_meld": 3.0,
            "pair": 1.5,
            "tatsu": 0.8,
            "isolated_penalty": -0.5,
            "isolated_reduction": 2.0,
            "structure_clarity": 1.5,
            "completion_improvement": 1.0
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
        """
        Enhanced discard logic for TempoDefender:
        - Considers hand completion level
        - Uses dynamic weights based on round progression
        - Evaluates post-discard hand quality
        - Considers opponent discard patterns
        """
        tiles = hand.tiles
        if not tiles:
            return None
        
        discard_pile = table_state.discard_pile
        
        # Calculate hand completion
        hand_completion = _hand_completion_score(hand, self.weights)
        
        # Get dynamic weights based on hand completion and turn progression
        dynamic_weights = _get_dynamic_weights(
            self.weights, 
            hand_completion, 
            table_state.turn, 
            table_state.wall_remaining
        )
        
        # Get opponent suit availability
        suit_availability = _opponent_suit_availability(
            discard_pile, 
            table_state.opponent_discards_by_suit
        )
        
        scored = []
        for t in tiles:
            # Base meld potential
            potential = _meld_potential_score(t, tiles, dynamic_weights)
            
            # Safety score (adjusted by dynamic weights)
            safety = _safety_score(t, discard_pile)
            safety_weighted = safety * dynamic_weights.get("safety_weight", 0.3)
            
            # Suit availability bonus (if suit is frequently discarded by opponents)
            suit_bonus = 0
            if t.tile_type in suit_availability:
                suit_bonus = suit_availability[t.tile_type] * 0.5  # Bonus for available suits
            
            # Post-discard hand quality evaluation
            post_discard_score = _evaluate_post_discard_hand(hand, t, dynamic_weights)
            
            # Combined score: lower = better to discard
            # TempoDefender prioritizes: safety > post-discard quality > potential
            discard_score = (
                -safety_weighted * 2.0 +  # Negative: safer tiles are better to discard
                -post_discard_score * 1.5 +  # Negative: better post-discard = better to discard
                potential * 0.5 -  # Lower potential = better to discard
                suit_bonus  # Available suits slightly less preferred to discard
            )
            
            scored.append((discard_score, t))
        
        # Sort by discard_score (lower = better to discard)
        scored.sort(key=lambda x: x[0])
        return scored[0][1] if scored else None


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
            "safety_weight": 0.3,
            "completed_meld": 3.0,
            "pair": 1.5,
            "tatsu": 0.8,
            "isolated_penalty": -0.5,
            "isolated_reduction": 2.0,
            "structure_clarity": 1.5,
            "completion_improvement": 1.0
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
        """
        Enhanced discard logic for ValueChaser:
        - Strongly prioritizes dominant suit retention
        - Considers hand completion for strategic decisions
        - Uses dynamic weights based on round progression
        - Evaluates post-discard hand quality
        - Considers opponent discard patterns for suit selection
        """
        tiles = hand.tiles
        if not tiles:
            return None
        
        discard_pile = table_state.discard_pile
        dominant_suit = _suit_majority(tiles)
        
        # Calculate hand completion
        hand_completion = _hand_completion_score(hand, self.weights)
        
        # Get dynamic weights based on hand completion and turn progression
        dynamic_weights = _get_dynamic_weights(
            self.weights, 
            hand_completion, 
            table_state.turn, 
            table_state.wall_remaining
        )
        
        # Get opponent suit availability
        suit_availability = _opponent_suit_availability(
            discard_pile, 
            table_state.opponent_discards_by_suit
        )
        
        scored = []
        for t in tiles:
            # Strong suit penalty for non-dominant suits (ValueChaser signature)
            suit_penalty = 0
            if dominant_suit and t.tile_type != dominant_suit and t.tile_type.name not in ["FENG", "JIAN"]:
                suit_penalty = dynamic_weights.get("suit_penalty", 2)
            
            # Base meld potential
            potential = _meld_potential_score(t, tiles, dynamic_weights)
            
            # Safety score (lower weight for ValueChaser - more risk-tolerant)
            safety = _safety_score(t, discard_pile)
            safety_weighted = safety * dynamic_weights.get("safety_weight", 0.3) * 0.5  # Reduced weight
            
            # Suit availability consideration
            # ValueChaser prefers to keep tiles from suits opponents are discarding (more available)
            suit_availability_bonus = 0
            if t.tile_type in suit_availability:
                suit_availability_bonus = suit_availability[t.tile_type] * 1.0  # Strong preference
            
            # Post-discard hand quality evaluation
            post_discard_score = _evaluate_post_discard_hand(hand, t, dynamic_weights)
            
            # Combined keep score: higher = better to keep
            # ValueChaser prioritizes: dominant suit > suit availability > potential > post-discard quality
            keep_score = (
                potential +
                safety_weighted +
                suit_availability_bonus +
                post_discard_score * 0.8 -
                suit_penalty  # Strong penalty for non-dominant suits
            )
            
            scored.append((keep_score, t))
        
        # Sort by keep_score (lower = better to discard)
        scored.sort(key=lambda x: x[0])
        return scored[0][1] if scored else None

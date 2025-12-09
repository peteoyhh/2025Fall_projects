"""
Real Monte Carlo simulation for Beijing Mahjong.

This is the unified simulation module that combines:
- Core game mechanics (tiles, hands, players)
- Table simulation (4-player games)
- Single-player simulation
- Utility calculation
- All experiment interfaces

All simulation uses actual tile-based gameplay with 136 tiles.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Set, Callable, Union, Any
from enum import Enum
from collections import Counter
import random
import time

# Import scoring functions
from .scoring import (
    compute_score,
    compute_winner_profit,
    compute_loser_cost
)
from .strategies import defensive_strategy, aggressive_strategy

# Initialize random seed based on current time to ensure different results on each run
# This ensures that each program execution produces different random sequences
random.seed(int(time.time() * 1000000) % (2**32))
np.random.seed(int(time.time() * 1000000) % (2**32))


def compute_utility(profit: float, missed_hu: bool, deal_in_as_loser: bool, 
                   missed_penalty: float = 0.2, deal_in_penalty: float = 0.5,
                   fan: int = 0) -> float:
    """
    Compute utility using strong concave reward function with minimal penalties.
    
    U = concave_reward(profit) - small_penalties
    
    Key design principles:
    - Strong concave (non-linear) reward function for positive profits
    - Utility is monotone increasing with profit
    - Penalties are minimal and do not overpower rewards
    - Winners always have strongly positive utility contribution
    - From fan >= 2, utility reward is multiplied by 10
    
    Args:
        profit: Profit from the hand (can be negative if lost)
        missed_hu: Boolean indicating if player missed a possible Hu
        deal_in_as_loser: Boolean indicating if player dealt in as loser
        missed_penalty: Penalty for missing a Hu (default: 0.2, greatly reduced)
        deal_in_penalty: Penalty for dealing in as loser (default: 0.5, greatly reduced)
        fan: Fan count of the hand (default: 0, used for bonus multiplier)
    
    Returns:
        Utility value
    """
    # Base utility calculation: sqrt(profit) * 3
    # Then multiply by 3 again if fan >= 2 (total 9x for fan >= 2)
    if profit > 0:
        # Positive profit: sqrt(profit) * 3
        utility = np.sqrt(profit) * 3
        
        # Multiply utility reward by 3 again for fan >= 2 (total 9x)
        if fan >= 2:
            utility *= 3
    elif profit < 0:
        # Negative profit: -sqrt(abs(profit)) * 3
        utility = -np.sqrt(abs(profit)) * 3
    else:
        # Zero profit
        utility = 0.0
    
    # Apply minimal penalties only when they occur
    # Penalties are greatly reduced to not overpower the concave rewards
    if missed_hu:
        utility -= missed_penalty
    
    if deal_in_as_loser:
        utility -= deal_in_penalty
    
    return utility


class TileType(Enum):
    """Mahjong tile types"""
    WAN = "wan"      # 1-9 wan
    TIAO = "tiao"    # 1-9 tiao
    TONG = "tong"    # 1-9 tong
    FENG = "feng"    # East, South, West, North
    JIAN = "jian"    # Zhong, Fa, Bai


class Tile:
    """Single mahjong tile"""
    def __init__(self, tile_type: TileType, value: int):
        self.tile_type = tile_type
        self.value = value  # 1-9 for wan/tiao/tong, 1-4 for feng, 1-3 for jian
    
    def __eq__(self, other):
        if not isinstance(other, Tile):
            return False
        return self.tile_type == other.tile_type and self.value == other.value
    
    def __hash__(self):
        return hash((self.tile_type, self.value))
    
    def __repr__(self):
        return f"Tile({self.tile_type.value}, {self.value})"
    
    def __lt__(self, other):
        """For sorting"""
        type_order = {TileType.WAN: 0, TileType.TIAO: 1, TileType.TONG: 2, 
                     TileType.FENG: 3, TileType.JIAN: 4}
        if self.tile_type != other.tile_type:
            return type_order.get(self.tile_type, 5) < type_order.get(other.tile_type, 5)
        return self.value < other.value
    
    def is_same_suit(self, other):
        """Check if same suit (for sequences)"""
        return (self.tile_type == other.tile_type and 
                self.tile_type in [TileType.WAN, TileType.TIAO, TileType.TONG])
    
    def is_next(self, other):
        """Check if other is next in sequence"""
        return (self.is_same_suit(other) and 
                self.value + 1 == other.value)


class TileWall:
    """Tile wall - 136 mahjong tiles"""
    def __init__(self):
        self.tiles = self._create_full_deck()
        self.shuffle()
        self.index = 0
    
    def _create_full_deck(self) -> List[Tile]:
        """Create full 136-tile deck"""
        tiles = []
        
        # Wan, Tiao, Tong: 36 each (4 copies of 1-9)
        for tile_type in [TileType.WAN, TileType.TIAO, TileType.TONG]:
            for value in range(1, 10):
                for _ in range(4):
                    tiles.append(Tile(tile_type, value))
        
        # Feng: 28 tiles (4 copies of East=1, South=2, West=3, North=4)
        for value in range(1, 5):
            for _ in range(4):
                tiles.append(Tile(TileType.FENG, value))
        
        # Jian: 12 tiles (4 copies of Zhong=1, Fa=2, Bai=3)
        for value in range(1, 4):
            for _ in range(4):
                tiles.append(Tile(TileType.JIAN, value))
        
        return tiles
    
    def shuffle(self):
        """Shuffle tiles"""
        random.shuffle(self.tiles)
        self.index = 0
    
    def draw(self) -> Optional[Tile]:
        """Draw one tile from wall"""
        if self.index >= len(self.tiles):
            return None
        tile = self.tiles[self.index]
        self.index += 1
        return tile
    
    def remaining(self) -> int:
        """Remaining tiles"""
        return len(self.tiles) - self.index


class Hand:
    """Player hand"""
    def __init__(self):
        self.tiles: List[Tile] = []  # Hand tiles
        self.melds: List[List[Tile]] = []  # All melds (Pungs, Chows, Kongs, Pair)
        # Meld types:
        # - Pung (triplet): 3 tiles
        # - Chow (sequence): 3 tiles
        # - Kong (quad): 4 tiles (upgraded from Pung)
        # - Pair: 2 tiles (part of winning requirement)
        self.concealed_meld_indices: Set[int] = set()  # Indices of concealed melds (for fan calculation)
        self.is_ready = False  # Ready to win
    
    def add_tile(self, tile: Tile):
        """Add tile to hand"""
        self.tiles.append(tile)
        self.tiles.sort()
    
    def remove_tile(self, tile: Tile) -> bool:
        """Remove tile from hand"""
        try:
            self.tiles.remove(tile)
            return True
        except ValueError:
            return False
    
    def add_meld(self, meld: List[Tile], remove_from_hand: bool = False, is_concealed: bool = False):
        """
        Add meld (creates a copy to ensure immutability).
        
        Meld can be:
        - Pung (triplet): 3 tiles
        - Chow (sequence): 3 tiles
        - Kong (quad): 4 tiles (upgraded from Pung)
        - Pair: 2 tiles (part of winning requirement)
        
        Args:
            meld: List of tiles in the meld
            remove_from_hand: If True, remove tiles from hand
                             If False, tiles already removed (for Pung/exposed melds)
            is_concealed: If True, mark this meld as concealed (for fan calculation)
        """
        meld_index = len(self.melds)
        self.melds.append(meld.copy())
        # Remove tiles from hand if needed
        if remove_from_hand:
            for tile in meld:
                self.remove_tile(tile)
        # Mark as concealed if specified (for fan calculation)
        if is_concealed:
            self.concealed_meld_indices.add(meld_index)
    
    def get_tile_counts(self) -> Dict[Tile, int]:
        """Get count of each tile"""
        return Counter(self.tiles)
    
    def can_peng(self, discarded_tile: Tile) -> bool:
        """
        Check if can Peng (triplet).
        """
        count = sum(1 for t in self.tiles if t == discarded_tile)
        return count >= 2
    
    def can_kong(self, tile: Tile = None) -> Optional[int]:
        """
        Check if can Kong (upgrade existing Pung meld to Kong).
        
        Kong can only be formed by upgrading an existing Pung meld:
        - Self-draw: if player has a Pung meld and draws the 4th identical tile
        - From discard: if player has a Pung meld and another player discards the 4th identical tile
        
        Args:
            tile: The tile to check (drawn tile or discarded tile). If None, checks hand tiles.
        
        Returns:
            Index of Pung meld that can be upgraded to Kong, or None if no upgrade possible
        """
        if tile:
            # Check if any existing Pung meld matches this tile
            for i, meld in enumerate(self.melds):
                if len(meld) == 3 and meld[0] == tile:
                    # This Pung meld can be upgraded to Kong
                    return i
        else:
            # Check hand tiles for 4th tile of any Pung meld
            for i, meld in enumerate(self.melds):
                if len(meld) == 3:
                    pung_tile = meld[0]
                    count = sum(1 for t in self.tiles if t == pung_tile)
                    if count >= 1:
                        # Have the 4th tile, can upgrade Pung to Kong
                        return i
        return None
    
    def can_chow(self, discarded_tile: Tile) -> List[List[Tile]]:
        """
        Check if can Chow (sequence) from discard.
        
        Chow can only be formed from discard (not self-drawn in this variant).
        
        Returns list of possible chow sequences.
        """
        chows = []
        if discarded_tile.tile_type not in [TileType.WAN, TileType.TIAO, TileType.TONG]:
            return []  # Only suited tiles can form chows
        
        # Check for chow sequences (e.g., 4-5-6, need 4 and 5 or 5 and 6 or 6 and 7)
        if discarded_tile.value >= 3:  # Can be middle or end of sequence
            # Check for sequence ending with discard (e.g., 3-4-5, discard is 5)
            tile_minus2 = Tile(discarded_tile.tile_type, discarded_tile.value - 2)
            tile_minus1 = Tile(discarded_tile.tile_type, discarded_tile.value - 1)
            if tile_minus2 in self.tiles and tile_minus1 in self.tiles:
                chows.append([tile_minus2, tile_minus1, discarded_tile])
        
        if 2 <= discarded_tile.value <= 8:  # Can be middle of sequence
            # Check for sequence with discard in middle (e.g., 4-5-6, discard is 5)
            tile_minus1 = Tile(discarded_tile.tile_type, discarded_tile.value - 1)
            tile_plus1 = Tile(discarded_tile.tile_type, discarded_tile.value + 1)
            if tile_minus1 in self.tiles and tile_plus1 in self.tiles:
                chows.append([tile_minus1, discarded_tile, tile_plus1])
        
        if discarded_tile.value <= 7:  # Can be start of sequence
            # Check for sequence starting with discard (e.g., 4-5-6, discard is 4)
            tile_plus1 = Tile(discarded_tile.tile_type, discarded_tile.value + 1)
            tile_plus2 = Tile(discarded_tile.tile_type, discarded_tile.value + 2)
            if tile_plus1 in self.tiles and tile_plus2 in self.tiles:
                chows.append([discarded_tile, tile_plus1, tile_plus2])
        
        return chows
    
    def check_winning_hand(self) -> Tuple[bool, List[List[Tile]]]:
        """
        Check if hand is winning (Hu).
        Returns (is_winning, list_of_melds_for_winning_pattern)
        
        Winning rule: 4 melds (pungs/chows/kongs) + 1 pair
        Meld types:
        - Pung (triplet): 3 identical tiles
        - Chow (sequence): 3 consecutive suited tiles
        - Pair: 2 identical tiles
        
        NOTE: This check ignores tile count - it only evaluates whether the tile multiset
        can form the required structure, regardless of how many tiles are currently in hand.
        """
        # Collect all tiles: hand tiles + melds
        all_tiles = self.tiles.copy()
        for meld in self.melds:
            all_tiles.extend(meld)
        
        # Try to find winning pattern (ignores tile count)
        return self._find_winning_pattern(all_tiles)
    
    def _find_winning_pattern(self, tiles: List[Tile]) -> Tuple[bool, List[List[Tile]]]:
        """
        Find winning pattern: 4 melds + 1 pair
        
        NOTE: This method ignores tile count. It only checks if the tile multiset
        can be decomposed into 4 melds (pung/chow) + 1 pair, regardless of total count.
        If there are extra tiles, we try all possible pairs and see if any combination works.
        """
        if len(tiles) == 0:
            return False, []
        
        # If we have exactly 14 tiles, use the standard algorithm
        if len(tiles) == 14:
            tile_counts = Counter(tiles)
            for pair_tile, count in tile_counts.items():
                if count >= 2:
                    remaining = tiles.copy()
                    remaining.remove(pair_tile)
                    remaining.remove(pair_tile)
                    melds = self._form_melds(remaining)
                    if melds is not None and len(melds) == 4:
                        return True, melds + [[pair_tile, pair_tile]]
            return False, []
        
        # If we have more or fewer tiles, try all possible pairs
        # and see if we can form 4 melds from the remaining tiles
        tile_counts = Counter(tiles)
        
        # Try each possible pair
        for pair_tile, count in tile_counts.items():
            if count >= 2:
                # Remove pair
                remaining = tiles.copy()
                remaining.remove(pair_tile)
                remaining.remove(pair_tile)
                
                # Try to form 4 melds from remaining tiles
                # The _form_melds method will handle extra tiles by finding exactly 4 melds
                melds = self._form_melds(remaining)
                if melds is not None and len(melds) == 4:
                    return True, melds + [[pair_tile, pair_tile]]
        
        return False, []
    
    def _form_melds(self, tiles: List[Tile]) -> Optional[List[List[Tile]]]:
        """
        Try to form melds (triplets or sequences) from tiles.
        
        Returns 4 melds if possible, None otherwise.
        NOTE: We need exactly 4 melds (12 tiles), but we allow extra tiles to be ignored.
        The recursive algorithm will naturally handle extra tiles by only using what it needs.
        """
        if len(tiles) == 0:
            return []
        
        # We need exactly 4 melds, so we need at least 12 tiles (4 * 3)
        if len(tiles) < 12:
            return None
        
        # The recursive algorithm will try to form exactly 4 melds
        # If there are extra tiles, they will be ignored (the algorithm stops when it finds 4 melds)
        tiles_sorted = sorted(tiles)
        result = self._form_melds_recursive(tiles_sorted, [])
        return result if result else None
    
    def _form_melds_recursive(self, tiles: List[Tile], current_melds: List[List[Tile]]) -> Optional[List[List[Tile]]]:
        """
        Recursively try to form melds.
        
        NOTE: This method will stop as soon as it finds exactly 4 melds,
        even if there are extra tiles remaining. This allows the algorithm
        to work with tile counts greater than 12.
        """
        # If we already have 4 melds, we're done (even if there are extra tiles)
        if len(current_melds) == 4:
            return current_melds
        
        if len(tiles) == 0:
            return current_melds if len(current_melds) == 4 else None
        
        if len(tiles) < 3:
            return None
        
        # Try triplet first
        first_tile = tiles[0]
        count = sum(1 for t in tiles if t == first_tile)
        
        if count >= 3:
            # Try triplet
            remaining = tiles.copy()
            for _ in range(3):
                remaining.remove(first_tile)
            result = self._form_melds_recursive(remaining, current_melds + [[first_tile, first_tile, first_tile]])
            if result:
                return result
        
        # Try sequence (only for wan/tiao/tong)
        if first_tile.tile_type in [TileType.WAN, TileType.TIAO, TileType.TONG]:
            if first_tile.value <= 7:  # Can form sequence
                next1 = Tile(first_tile.tile_type, first_tile.value + 1)
                next2 = Tile(first_tile.tile_type, first_tile.value + 2)
                
                if next1 in tiles and next2 in tiles:
                    remaining = tiles.copy()
                    remaining.remove(first_tile)
                    remaining.remove(next1)
                    remaining.remove(next2)
                    result = self._form_melds_recursive(remaining, current_melds + [[first_tile, next1, next2]])
                    if result:
                        return result
        
        return None


class FanCalculator:
    """Calculate fan (points) for winning hand"""
    
    @staticmethod
    def calculate_fan(hand: Hand, is_self_draw: bool, is_dealer: bool) -> int:
        """
        Calculate total fan for winning hand.
        
        Args:
            hand: The winning hand
            is_self_draw: Whether win was self-draw
            is_dealer: Whether winner is dealer
        """
        fan = 0
        
        # Get all tiles in hand
        all_tiles = hand.tiles.copy()
        for meld in hand.melds:
            all_tiles.extend(meld)
        
        tile_counts = Counter(all_tiles)
        
        # Get winning pattern structure
        is_winning, winning_melds = hand.check_winning_hand()
        if not is_winning:
            return 0  # Invalid hand
        
        # Analyze meld structure
        triplets, sequences = FanCalculator._analyze_melds(hand, winning_melds)
        
        # ===== 1. Basic Hand — 1 Fan Each =====
        
        # ① Self-draw — 1 fan
        if is_self_draw:
            fan += 1
        
        # ② Concealed hand — 1 fan
        # No exposed melds (all melds are concealed)
        # For concealed hand, we check if there are any melds at all
        # Actually, if melds exist, they are exposed (Peng from discard)
        # So concealed hand means no melds
        if len(hand.melds) == 0:
            fan += 1
        
        # ③ All simples — 1 fan
        # No terminals (1 or 9) and no honors
        if FanCalculator._is_all_simples(all_tiles):
            fan += 1
        
        # ===== 2. Common Wins — 2 Fan Each =====
        
        # ④ All pungs — 2 fan
        # Hand consists of four pung sets and one pair
        if len(triplets) == 4 and len(sequences) == 0:
            fan += 2
        
        # ⑤ Mixed triple chow — 2 fan
        # Same numbered chow appears in all three suits
        if FanCalculator._has_mixed_triple_chow(hand, winning_melds):
            fan += 2
        
        # ===== 3. Advanced Hands — 4–6 Fan Each =====
        
        # ⑥ Pure flush — 4–6 fan
        # Whole hand uses tiles from one suit, no honors
        pure_flush_result = FanCalculator._is_pure_flush(all_tiles, len(hand.melds) == 0)
        if pure_flush_result:
            fan += pure_flush_result  # 4 fan if exposed, 6 fan if concealed
        
        # ⑦ Little dragons — 4–6 fan
        # Two dragon pungs + pair made from the remaining dragon
        little_dragons_result = FanCalculator._is_little_dragons(hand, winning_melds)
        if little_dragons_result:
            fan += little_dragons_result  # 4 fan if exposed, 6 fan if concealed
        
        # ===== 4. Add-on Bonuses — +1 to +2 Fan =====
        
        # ⑧ Kong — +1 fan per kong
        # Count kongs (4-tile melds)
        # Kongs can be in hand.melds (exposed) or in winning_melds (concealed from hand tiles)
        kong_count = 0
        # Count exposed kongs (in hand.melds)
        for meld in hand.melds:
            if len(meld) == 4:
                kong_count += 1
        # Count concealed kongs (in winning_melds but not in hand.melds)
        # A kong in winning_melds is concealed if it's not already in hand.melds
        for meld in winning_melds:
            if len(meld) == 4:
                # Check if this kong is already counted in hand.melds
                is_already_counted = False
                for exposed_meld in hand.melds:
                    if len(exposed_meld) == 4 and exposed_meld[0] == meld[0]:
                        is_already_counted = True
                        break
                if not is_already_counted:
                    kong_count += 1
        fan += kong_count  # +1 fan per kong
        
        # ⑨ "Kong open" win — +1 fan
        # This is handled by checking if the winning tile was drawn after a kong
        # For now, we don't track this in the current implementation
        # (would need to pass a flag indicating if this is a "kong open" win)
        
        # Ensure minimum 1 fan (Pi Hu with 1 fan is allowed)
        if fan == 0:
            fan = 1
        
        # Cap at 16 fan
        return min(fan, 16)
    
    @staticmethod
    def _analyze_melds(hand: Hand, winning_melds: List[List[Tile]]) -> Tuple[List[Tile], List[List[Tile]]]:
        """
        Analyze melds to identify triplets and sequences.
        Returns (list of triplet tiles, list of sequence melds)
        """
        triplets = []
        sequences = []
        seen_triplets = set()  # Track seen triplets to avoid duplicates
        
        # Check all melds
        for meld in hand.melds:
            if len(meld) >= 3:
                if meld[0] == meld[1] == meld[2]:
                    # Triplet
                    tile_key = (meld[0].tile_type, meld[0].value)
                    if tile_key not in seen_triplets:
                        triplets.append(meld[0])
                        seen_triplets.add(tile_key)
                elif (meld[0].tile_type in [TileType.WAN, TileType.TIAO, TileType.TONG] and
                      meld[0].value + 1 == meld[1].value and
                      meld[1].value + 1 == meld[2].value):
                    # Sequence
                    sequences.append(meld[:3])
        
        # Check winning pattern melds (from hand tiles)
        # winning_melds contains 4 melds + 1 pair
        for meld in winning_melds:
            if len(meld) == 2:
                continue  # Skip pair
            if len(meld) >= 3:
                if meld[0] == meld[1] == meld[2]:
                    # Triplet
                    tile_key = (meld[0].tile_type, meld[0].value)
                    if tile_key not in seen_triplets:
                        triplets.append(meld[0])
                        seen_triplets.add(tile_key)
                elif (meld[0].tile_type in [TileType.WAN, TileType.TIAO, TileType.TONG] and
                      meld[0].value + 1 == meld[1].value and
                      meld[1].value + 1 == meld[2].value):
                    # Sequence
                    sequences.append(meld[:3])
        
        return triplets, sequences
    
    @staticmethod
    def _is_all_simples(tiles: List[Tile]) -> bool:
        """
        Check if all tiles are simples (2-8 only, no terminals 1/9, no honors).
        """
        if not tiles:
            return False
        for tile in tiles:
            if tile.tile_type in [TileType.FENG, TileType.JIAN]:
                return False  # Honors not allowed
            if tile.tile_type in [TileType.WAN, TileType.TIAO, TileType.TONG]:
                if tile.value == 1 or tile.value == 9:
                    return False  # Terminals not allowed
        return True
    
    @staticmethod
    def _has_mixed_triple_chow(hand: Hand, winning_melds: List[List[Tile]]) -> bool:
        """
        Check if hand has mixed triple chow (same numbered chow in all three suits).
        Example: 4-5-6 in wan, tiao, tong
        
        Checks both exposed melds and winning pattern melds.
        """
        sequences = []
        
        # Check exposed melds
        for meld in hand.melds:
            if len(meld) == 3:
                if (meld[0].tile_type in [TileType.WAN, TileType.TIAO, TileType.TONG] and
                    meld[0].value + 1 == meld[1].value and
                    meld[1].value + 1 == meld[2].value):
                    sequences.append((meld[0].tile_type, meld[0].value))
        
        # Check winning pattern melds
        for meld in winning_melds:
            if len(meld) == 3:
                if (meld[0].tile_type in [TileType.WAN, TileType.TIAO, TileType.TONG] and
                    meld[0].value + 1 == meld[1].value and
                    meld[1].value + 1 == meld[2].value):
                    sequences.append((meld[0].tile_type, meld[0].value))
        
        # Group sequences by value
        by_value = {}
        for suit, value in sequences:
            if value not in by_value:
                by_value[value] = set()
            by_value[value].add(suit)
        
        # Check if any value has sequences in all three suits
        for value, suits in by_value.items():
            if len(suits) == 3 and TileType.WAN in suits and TileType.TIAO in suits and TileType.TONG in suits:
                return True
        
        return False
    
    @staticmethod
    def _is_pure_flush(tiles: List[Tile], is_concealed: bool) -> int:
        """
        Check if hand is pure flush (all one suit, no honors).
        Returns 4 fan if exposed, 6 fan if concealed, 0 if not pure flush.
        """
        if not tiles:
            return 0
        
        # Must be all from one suit (wan/tiao/tong), no honors
        suits = set()
        for tile in tiles:
            if tile.tile_type in [TileType.FENG, TileType.JIAN]:
                return 0  # Honors not allowed
            if tile.tile_type in [TileType.WAN, TileType.TIAO, TileType.TONG]:
                suits.add(tile.tile_type)
        
        if len(suits) == 1:
            return 6 if is_concealed else 4
        
        return 0
    
    @staticmethod
    def _is_little_dragons(hand: Hand, winning_melds: List[List[Tile]]) -> int:
        """
        Check if hand is little dragons (two dragon pungs + pair of third dragon).
        Returns 4 fan if exposed, 6 fan if concealed, 0 if not little dragons.
        """
        # Get all melds (exposed + winning pattern)
        all_melds = hand.melds.copy()
        all_melds.extend(winning_melds)
        
        # Count dragon melds and find pair
        dragon_melds = []
        dragon_pair = None
        
        for meld in all_melds:
            if len(meld) == 2:
                # Check if pair is a dragon
                if meld[0].tile_type == TileType.JIAN and meld[0] == meld[1]:
                    dragon_pair = meld[0]
            elif len(meld) >= 3:
                # Check if meld is a dragon triplet
                if (meld[0].tile_type == TileType.JIAN and 
                    meld[0] == meld[1] == meld[2]):
                    dragon_melds.append(meld[0])
        
        # Need exactly 2 dragon melds and 1 dragon pair
        if len(dragon_melds) == 2 and dragon_pair is not None:
            # Check that the pair is the third dragon (not one of the melds)
            used_dragons = set(dragon_melds)
            if dragon_pair not in used_dragons:
                # Check if concealed (no exposed melds)
                is_concealed = len(hand.melds) == 0
                return 6 if is_concealed else 4
        
        return 0


class Player:
    """Mahjong player"""
    def __init__(self, player_id: int, strategy_type: str, strategy_fn=None):
        self.player_id = player_id
        self.strategy_type = strategy_type  # "DEF" or "AGG"
        self.strategy_fn = strategy_fn
        self.hand = Hand()
        self.is_dealer = False
        self.profit = 0.0
        self.utility = 0.0
        self.wins = 0
        self.deal_ins = 0
        self.missed_hus = 0
    
    def should_hu(self, fan: int, fan_min: int = 1, fan_threshold: int = 3, risk: float = 0.0) -> bool:
        """Strategy decision: should declare Hu?"""
        if self.strategy_type == "DEF":
            return fan >= fan_min
        elif self.strategy_type == "AGG":
            return fan >= fan_threshold
        elif self.strategy_type == "NEU":
            # Neutral policy: if risk > 0.4 -> Hu immediately, if fan >= 1 -> Hu
            if risk > 0.4:
                return True
            if fan >= 1:
                return True
            # Otherwise 20% chance to continue
            return random.random() >= 0.2
        elif self.strategy_fn:
            return self.strategy_fn(fan)
        return fan >= 1
    
    def decide_discard(self) -> Optional[Tile]:
        """Decide which tile to discard"""
        if not self.hand.tiles:
            return None
        
        # Simple strategy: discard first tile
        # In real game, would use more sophisticated strategy
        return self.hand.tiles[0]
    
    def can_win_on_tile(self, tile: Tile, is_self_draw: bool = False) -> Tuple[bool, int]:
        """Check if can win with this tile, return (can_win, fan)"""
        # Add tile temporarily
        self.hand.add_tile(tile)
        can_win, _ = self.hand.check_winning_hand()
        
        if can_win:
            # Calculate fan
            fan = FanCalculator.calculate_fan(self.hand, is_self_draw=is_self_draw, 
                                             is_dealer=self.is_dealer)
            # Remove tile (should always succeed since we just added it)
            self.hand.remove_tile(tile)
            return True, fan
        else:
            # Remove tile (should always succeed since we just added it)
            self.hand.remove_tile(tile)
            return False, 0


class RealMCSimulation:
    """Real Monte Carlo simulation of Mahjong game"""
    
    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.wall = None
        self.players: List[Player] = []
        self.current_player = 0
        self.discard_pile: List[Tile] = []
        self.round_results: List[Dict] = []
    
    def initialize_round(self, players: List[Player], dealer_index: int = 0):
        """Initialize a new round"""
        self.wall = TileWall()
        self.players = players
        self.current_player = dealer_index
        self.discard_pile = []
        self.round_results = []
        
        # Set dealer
        for i, player in enumerate(self.players):
            player.is_dealer = (i == dealer_index)
            player.hand = Hand()  # New hand resets concealed_meld_indices
        
        # Deal initial tiles: 13 tiles each (dealer gets 14)
        for _ in range(3):  # 3 rounds of 4 tiles
            for player in self.players:
                for _ in range(4):
                    tile = self.wall.draw()
                    if tile:
                        player.hand.add_tile(tile)
        
        # Deal one more tile to each (13 total)
        for player in self.players:
            tile = self.wall.draw()
            if tile:
                player.hand.add_tile(tile)
        
        # Dealer gets one more tile (14 total)
        dealer_tile = self.wall.draw()
        if dealer_tile:
            self.players[dealer_index].hand.add_tile(dealer_tile)
    
    def simulate_round(self) -> Dict:
        """Simulate one complete round"""
        max_turns = 100  # Safety limit
        turn = 0
        
        while turn < max_turns and self.wall.remaining() > 0:
            player = self.players[self.current_player]
            
            # Draw tile
            drawn_tile = self.wall.draw()
            if not drawn_tile:
                break  # Wall exhausted
            
            player.hand.add_tile(drawn_tile)
            
            # Check if win FIRST (after draw)
            can_win, fan = player.can_win_on_tile(drawn_tile, is_self_draw=True)
            
            if can_win:
                # Strategy decision
                fan_min = self.cfg.get("fan_min", 1)
                fan_threshold = self.cfg.get("t_fan_threshold", 3)
                # Estimate risk (simplified: based on discard pile size)
                risk = len(self.discard_pile) / max(100, self.wall.remaining() + len(self.discard_pile))
                
                if player.should_hu(fan, fan_min, fan_threshold, risk):
                    # Player wins!
                    return self._process_win(player, fan, is_self_draw=True)
                else:
                    # Missed Hu opportunity
                    player.missed_hus += 1
            
            # If not win, check for Kong (upgrade existing Pung meld)
            # Kong can only be formed by upgrading an existing Pung meld
            kong_meld_idx = player.hand.can_kong(drawn_tile)
            if kong_meld_idx is not None:
                # Upgrade existing Pung meld to Kong
                old_pung = player.hand.melds[kong_meld_idx]
                # Remove the 4th tile from hand (drawn_tile)
                if player.hand.remove_tile(drawn_tile):
                    # Replace Pung with Kong (4 tiles)
                    kong_meld = old_pung.copy() + [drawn_tile]
                    player.hand.melds[kong_meld_idx] = kong_meld
                    # Kong is a fixed meld (no special marking needed)
                    
                    # Player restarts turn: continuously check for Kong and win after drawing replacement tiles
                    while True:
                        replacement = self.wall.draw()
                        if not replacement:
                            # Wall exhausted after Kong - end round as draw
                            return self._process_draw()
                        
                        player.hand.add_tile(replacement)
                        
                        # Check if can win on replacement tile FIRST
                        can_win_after_kong, fan_after_kong = player.can_win_on_tile(
                            replacement, is_self_draw=True)
                        if can_win_after_kong:
                            fan_min = self.cfg.get("fan_min", 1)
                            fan_threshold = self.cfg.get("t_fan_threshold", 3)
                            risk = len(self.discard_pile) / max(100, self.wall.remaining() + len(self.discard_pile))
                            if player.should_hu(fan_after_kong, fan_min, fan_threshold, risk):
                                return self._process_win(player, fan_after_kong, is_self_draw=True)
                        
                        # Check if can Kong again (upgrade another Pung meld)
                        kong_meld_idx = player.hand.can_kong(replacement)
                        if kong_meld_idx is not None:
                            # Upgrade another Pung meld to Kong
                            old_pung = player.hand.melds[kong_meld_idx]
                            if player.hand.remove_tile(replacement):
                                kong_meld = old_pung.copy() + [replacement]
                                player.hand.melds[kong_meld_idx] = kong_meld
                                # Continue loop to draw another replacement tile
                                continue
                            else:
                                # Should not happen, but break if remove fails
                                break
                        else:
                            # No more Kong possible, break and continue to discard
                            break
                    # After Kong(s), player continues turn (will discard in next iteration)
                    # current_player stays the same
                # If Kong was processed, skip Pung check and continue to discard
            else:
                # If no Kong, check for self-draw Pung
                # If player self-draws and has 3 identical tiles, can form pung
                tile_counts = player.hand.get_tile_counts()
                for tile, count in tile_counts.items():
                    if count == 3:
                        # Can form self-draw pung
                        pung_tiles = [t for t in player.hand.tiles if t == tile]
                        # Remove 3 tiles from hand
                        for _ in range(3):
                            if not player.hand.remove_tile(tile):
                                # Should not happen, but handle gracefully
                                break
                        # Add pung meld
                        player.hand.add_meld(pung_tiles, remove_from_hand=False, 
                                           is_concealed=False)
                        # After self-draw pung, continue to discard
                        break  # Only form one pung at a time
            
            # Note: Chow (sequence) can only be formed from discard, not self-drawn
            # So we don't check for self-draw chow here
            
            # Discard tile
            discard = player.decide_discard()
            if discard:
                player.hand.remove_tile(discard)
                self.discard_pile.append(discard)
                
                # Check other players' reactions in priority order: Hu > Kong > Peng > Chow
                # Players are checked in order: next player, opposite player, previous player
                action_taken = False
                num_players = len(self.players)
                
                # Get player order: next (current+1), opposite (current+2), previous (current+3)
                player_order = [
                    (self.current_player + offset) % num_players
                    for offset in [1, 2, 3]
                ]
                
                # Priority 1: Check for Hu (winning)
                for i in player_order:
                    other_player = self.players[i]
                    can_win_other, fan_other = other_player.can_win_on_tile(
                        discard, is_self_draw=False)
                    if can_win_other:
                        fan_min = self.cfg.get("fan_min", 1)
                        fan_threshold = self.cfg.get("t_fan_threshold", 3)
                        # Estimate risk for opponent
                        risk = len(self.discard_pile) / max(100, self.wall.remaining() + len(self.discard_pile))
                        if other_player.should_hu(fan_other, fan_min, fan_threshold, risk):
                            # Other player wins via deal-in
                            other_player.deal_ins += 1
                            return self._process_win(other_player, fan_other, 
                                                   is_self_draw=False, 
                                                   deal_in_player=player)
                
                # Priority 2: Check for Kong (upgrade existing Pung meld)
                if not action_taken:
                    for i in player_order:
                        other_player = self.players[i]
                        kong_meld_idx = other_player.hand.can_kong(discard)
                        if kong_meld_idx is not None:
                            # Upgrade existing Pung meld to Kong
                            old_pung = other_player.hand.melds[kong_meld_idx]
                            # Replace Pung with Kong (4 tiles: 3 from meld + discard)
                            kong_meld = old_pung.copy() + [discard]
                            other_player.hand.melds[kong_meld_idx] = kong_meld
                            # Kong is a fixed meld
                            
                            # Player restarts turn: continuously check for Kong and win after drawing replacement tiles
                            self.current_player = i
                            while True:
                                replacement = self.wall.draw()
                                if not replacement:
                                    # Wall exhausted after Kong - end round as draw
                                    return self._process_draw()
                                
                                other_player.hand.add_tile(replacement)
                                
                                # Check if can win on replacement tile FIRST
                                can_win_after_kong, fan_after_kong = other_player.can_win_on_tile(
                                    replacement, is_self_draw=True)
                                if can_win_after_kong:
                                    fan_min = self.cfg.get("fan_min", 1)
                                    fan_threshold = self.cfg.get("t_fan_threshold", 3)
                                    risk = len(self.discard_pile) / max(100, self.wall.remaining() + len(self.discard_pile))
                                    if other_player.should_hu(fan_after_kong, fan_min, fan_threshold, risk):
                                        return self._process_win(other_player, fan_after_kong, 
                                                                   is_self_draw=True)
                                
                                # Check if can Kong again (upgrade another Pung meld)
                                kong_meld_idx = other_player.hand.can_kong(replacement)
                                if kong_meld_idx is not None:
                                    # Upgrade another Pung meld to Kong
                                    old_pung = other_player.hand.melds[kong_meld_idx]
                                    if other_player.hand.remove_tile(replacement):
                                        kong_meld = old_pung.copy() + [replacement]
                                        other_player.hand.melds[kong_meld_idx] = kong_meld
                                        # Continue loop to draw another replacement tile
                                        continue
                                    else:
                                        # Should not happen, but break if remove fails
                                        break
                                else:
                                    # No more Kong possible, break and continue to discard
                                    break
                            # After Kong(s), player continues turn (will discard in next iteration)
                            
                            action_taken = True
                            break  # Only one player can Kong
                
                # Priority 3: Check for Peng (triplet) or Chow (sequence)
                if not action_taken:
                    for i in player_order:
                        other_player = self.players[i]
                        # Check for Peng first
                        if other_player.hand.can_peng(discard):
                            # Player does Peng from discard
                            # Remove 2 tiles from hand
                            for _ in range(2):
                                if not other_player.hand.remove_tile(discard):
                                    # Should not happen, but handle gracefully
                                    break
                            # Add exposed Peng (triplet) from discard
                            peng_meld = [discard, discard, discard]
                            other_player.hand.add_meld(peng_meld, remove_from_hand=False, 
                                                      is_concealed=False)
                            
                            # Player who did Peng continues (must discard in next iteration)
                            self.current_player = i
                            action_taken = True
                            break  # Only one player can Peng
                        # Check for Chow (sequence)
                        elif other_player.hand.can_chow(discard):
                            # Player does Chow from discard
                            chows = other_player.hand.can_chow(discard)
                            if chows:
                                chow_meld = chows[0]
                                # Remove 2 tiles from hand (discard is the 3rd)
                                for tile in chow_meld:
                                    if tile != discard:
                                        if not other_player.hand.remove_tile(tile):
                                            # Should not happen, but handle gracefully
                                            break
                                # Add exposed Chow (sequence) from discard
                                other_player.hand.add_meld(chow_meld, remove_from_hand=False, 
                                                          is_concealed=False)
                                
                                # Player who did Chow continues (must discard in next iteration)
                                self.current_player = i
                                action_taken = True
                                break  # Only one player can Chow
                
                # If no action taken, move to next player normally
                if not action_taken:
                    self.current_player = (self.current_player + 1) % len(self.players)
            else:
                # No discard available - this should not happen in normal gameplay
                # Possible causes: hand is empty (unexpected)
                # End round as draw to avoid infinite loop
                return self._process_draw()
            
            turn += 1
        
        # Round ended without winner (draw)
        return self._process_draw()
    
    def _process_win(self, winner: Player, fan: int, is_self_draw: bool, 
                    deal_in_player: Optional[Player] = None) -> Dict:
        """Process winning result"""
        score = compute_score(fan, self.cfg.get("base_points", 1))
        
        if is_self_draw:
            # Self-draw: winner gets from all 3 opponents
            winner_profit = compute_winner_profit(score, is_self_draw=True, deal_in_occurred=False)
            total_winner_profit = winner_profit * 3  # Total from 3 opponents
            winner.profit += total_winner_profit
            
            for player in self.players:
                if player != winner:
                    loser_cost = compute_loser_cost(score, self.cfg.get("penalty_deal_in", 3), 
                                                   is_deal_in_loser=False)
                    player.profit += loser_cost
        else:
            # Deal-in: winner gets from deal-in player only
            winner_profit = compute_winner_profit(score, is_self_draw=False, deal_in_occurred=True)
            total_winner_profit = winner_profit  # Total profit (same as single profit for deal-in)
            winner.profit += total_winner_profit
            
            if deal_in_player:
                loser_cost = compute_loser_cost(score, self.cfg.get("penalty_deal_in", 3), 
                                               is_deal_in_loser=True)
                deal_in_player.profit += loser_cost
        
        winner.wins += 1
        
        # Calculate utility using sqrt(profit) * 3, based on total profit for this round
        winner.utility += compute_utility(total_winner_profit, missed_hu=False, deal_in_as_loser=False, fan=fan)
        
        return {
            "winner": winner.player_id,
            "fan": fan,
            "is_self_draw": is_self_draw,
            "score": score,
            "winner_profit": winner_profit,
            "deal_in_player_id": deal_in_player.player_id if deal_in_player else None
        }
    
    def _process_draw(self) -> Dict:
        """Process draw (no winner)"""
        return {
            "winner": None,
            "fan": 0,
            "is_self_draw": False,
            "score": 0,
            "winner_profit": 0
        }


def simulate_real_mc_round(players: List[Player], cfg: Dict, dealer_index: int = 0) -> Dict:
    """Simulate one round with real Monte Carlo"""
    sim = RealMCSimulation(cfg)
    sim.initialize_round(players, dealer_index)
    result = sim.simulate_round()
    return result


def run_real_mc_trial(players: List[Player], cfg: Dict, rounds: int = 200) -> Dict:
    """Run one trial with multiple rounds"""
    dealer_index = 0
    
    for round_num in range(rounds):
        result = simulate_real_mc_round(players, cfg, dealer_index)
        
        # Update dealer (if dealer didn't win, rotate)
        if result["winner"] is not None:
            winner_idx = result["winner"]
            if players[winner_idx].is_dealer:
                # Dealer continues
                dealer_index = winner_idx
            else:
                # Rotate dealer
                dealer_index = (dealer_index + 1) % len(players)
        else:
            # Draw: rotate dealer
            dealer_index = (dealer_index + 1) % len(players)
    
    # Aggregate results
    results = {}
    for player in players:
        results[player.player_id] = {
            "profit": player.profit,
            "utility": player.utility,
            "wins": player.wins,
            "deal_ins": player.deal_ins,
            "missed_hus": player.missed_hus
        }
    
    return results


# ============================================================================
# Table Simulation Functions (from table.py)
# ============================================================================

def simulate_table_round(players, cfg, dealer_index):
    """
    Simulate a single round with 4 players using REAL Monte Carlo.
    
    Args:
        players: List of player dicts with "strategy" and "strategy_type"
        cfg: Configuration dictionary
        dealer_index: Index of dealer player
    
    Returns:
        (results, round_meta) tuple
    """
    # Convert player dicts to Player objects
    mc_players = []
    fan_min = cfg.get("fan_min", 1)
    fan_threshold = cfg.get("t_fan_threshold", 3)
    
    for i, player_dict in enumerate(players):
        strategy_type = player_dict.get("strategy_type", "NEU")
        strategy_fn = player_dict.get("strategy")
        
        mc_player = Player(i, strategy_type, strategy_fn)
        mc_player.is_dealer = (i == dealer_index)
        mc_players.append(mc_player)
    
    # Simulate round using real Monte Carlo
    result = simulate_real_mc_round(mc_players, cfg, dealer_index)
    
    # Convert result to expected format
    results = []
    winner_idx = result.get("winner")
    is_self_draw = result.get("is_self_draw", False)
    fan = result.get("fan", 0)
    winner_profit = result.get("winner_profit", 0.0)
    
    # Initialize all players with zero results
    for i in range(len(players)):
        results.append({
            "profit": 0.0,
            "utility": 0.0,
            "fan": 0,
            "won": False,
            "deal_in_as_winner": False,
            "deal_in_as_loser": False,
            "missed_hu": False
        })
    
    if winner_idx is not None:
        # Someone won
        winner = mc_players[winner_idx]
        results[winner_idx]["won"] = True
        results[winner_idx]["fan"] = fan
        results[winner_idx]["deal_in_as_winner"] = not is_self_draw
        
        # Calculate total profit for winner (self-draw: 3x, deal-in: 1x)
        if is_self_draw:
            total_winner_profit = winner_profit * 3
        else:
            total_winner_profit = winner_profit
        
        results[winner_idx]["profit"] = total_winner_profit
        results[winner_idx]["utility"] = compute_utility(
            total_winner_profit, 
            missed_hu=False, 
            deal_in_as_loser=False,
            fan=fan
        )
        
        # Calculate losses for other players
        score = compute_score(fan, cfg.get("base_points", 1))
        
        if is_self_draw:
            # Self-draw: all 3 opponents pay
            loser_cost = compute_loser_cost(
                score,
                cfg.get("penalty_deal_in", 3),
                is_deal_in_loser=False
            )
            for i in range(len(players)):
                if i != winner_idx:
                    results[i]["profit"] = loser_cost
                    results[i]["utility"] = compute_utility(
                        loser_cost,
                        missed_hu=False,
                        deal_in_as_loser=False,
                        fan=0
                    )
        else:
            # Deal-in: get deal_in_player from result
            deal_in_player_idx = result.get("deal_in_player_id")
            
            if deal_in_player_idx is not None:
                loser_cost = compute_loser_cost(
                    score,
                    cfg.get("penalty_deal_in", 3),
                    is_deal_in_loser=True
                )
                results[deal_in_player_idx]["profit"] = loser_cost
                results[deal_in_player_idx]["deal_in_as_loser"] = True
                results[deal_in_player_idx]["utility"] = compute_utility(
                    loser_cost,
                    missed_hu=False,
                    deal_in_as_loser=True,
                    fan=0
                )
            else:
                # Fallback: if deal_in_player_id is None but is_self_draw=False,
                # this should not happen in normal gameplay, but handle gracefully
                # In this case, we cannot determine who dealt in, so no one pays deal-in penalty
                # This is a safety fallback for edge cases
                pass
        
        # Check for missed Hu opportunities
        for i, player in enumerate(mc_players):
            if i != winner_idx and player.missed_hus > 0:
                results[i]["missed_hu"] = True
                # Update utility with missed Hu penalty
                results[i]["utility"] = compute_utility(
                    results[i]["profit"],
                    missed_hu=True,
                    deal_in_as_loser=results[i]["deal_in_as_loser"],
                    fan=0
                )
    
    # Round metadata
    round_meta = {
        "winner_index": winner_idx,
        "winner_is_dealer": winner_idx == dealer_index if winner_idx is not None else False,
        "dealer_ready": False,  # Not used in real MC
        "dealer_continues": winner_idx == dealer_index if winner_idx is not None else False,
        "is_draw": winner_idx is None
    }
    
    return results, round_meta


def _run_table(players, cfg, rounds_per_trial, baseline_utility=None):
    """Run table simulation with multiple rounds"""
    if baseline_utility is None:
        baseline_utility = cfg.get("baseline_utility", 50)
    dealer_index = 0

    player_count = len(players)

    all_profits = [[] for _ in range(player_count)]
    all_utilities = [[] for _ in range(player_count)]
    all_fans = [[] for _ in range(player_count)]
    all_wins = [[] for _ in range(player_count)]
    all_deal_in_as_winner = [[] for _ in range(player_count)]
    all_deal_in_as_loser = [[] for _ in range(player_count)]
    all_missed_hu = [[] for _ in range(player_count)]

    dealer_round_stats = {
        "profits": [],
        "utilities": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": [],
        "fans": []
    }

    non_dealer_round_stats = {
        "profits": [],
        "utilities": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": [],
        "fans": []
    }

    for _ in range(rounds_per_trial):
        round_results, round_meta = simulate_table_round(players, cfg, dealer_index)

        for i, result in enumerate(round_results):
            all_profits[i].append(result["profit"])
            all_utilities[i].append(result["utility"])
            all_fans[i].append(result["fan"])
            all_wins[i].append(result["won"])
            all_deal_in_as_winner[i].append(result["deal_in_as_winner"])
            all_deal_in_as_loser[i].append(result["deal_in_as_loser"])
            all_missed_hu[i].append(result["missed_hu"])

            target_stats = dealer_round_stats if i == dealer_index else non_dealer_round_stats
            target_stats["profits"].append(result["profit"])
            target_stats["utilities"].append(result["utility"])
            target_stats["wins"].append(result["won"])
            target_stats["deal_in_as_winner"].append(result["deal_in_as_winner"])
            target_stats["deal_in_as_loser"].append(result["deal_in_as_loser"])
            target_stats["missed_hu"].append(result["missed_hu"])
            target_stats["fans"].append(result["fan"])

        if not round_meta["dealer_continues"]:
            dealer_index = (dealer_index + 1) % player_count

    def_stats = {
        "profits": [],
        "utilities": [],
        "fans": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": []
    }

    agg_stats = {
        "profits": [],
        "utilities": [],
        "fans": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": []
    }

    per_player_stats = []

    for i, player in enumerate(players):
        profit_sum = np.sum(all_profits[i])
        utility_sum = baseline_utility + np.sum(all_utilities[i])
        wins = all_wins[i]
        fans = [f for f in all_fans[i] if f > 0]

        stats = {
            "profit": profit_sum,
            "utility": utility_sum,
            "mean_fan": np.mean(fans) if len(fans) > 0 else 0.0,
            "win_rate": np.mean(wins),
            "deal_in_rate": np.mean(all_deal_in_as_winner[i]),
            "deal_in_loss_rate": np.mean(all_deal_in_as_loser[i]),
            "missed_win_rate": np.mean(all_missed_hu[i]),
            "fan_distribution": all_fans[i]
        }

        per_player_stats.append({
            "player_index": i,
            "strategy_type": player.get("strategy_type"),
            **stats
        })

        if player.get("strategy_type") == "DEF":
            def_stats["profits"].append(stats["profit"])
            def_stats["utilities"].append(stats["utility"])
            def_stats["fans"].extend(fans)
            def_stats["wins"].append(stats["win_rate"])
            def_stats["deal_in_as_winner"].append(stats["deal_in_rate"])
            def_stats["deal_in_as_loser"].append(stats["deal_in_loss_rate"])
            def_stats["missed_hu"].append(stats["missed_win_rate"])
        elif player.get("strategy_type") == "AGG":
            agg_stats["profits"].append(stats["profit"])
            agg_stats["utilities"].append(stats["utility"])
            agg_stats["fans"].extend(fans)
            agg_stats["wins"].append(stats["win_rate"])
            agg_stats["deal_in_as_winner"].append(stats["deal_in_rate"])
            agg_stats["deal_in_as_loser"].append(stats["deal_in_loss_rate"])
            agg_stats["missed_hu"].append(stats["missed_win_rate"])

    return {
        "defensive": def_stats,
        "aggressive": agg_stats,
        "dealer": dealer_round_stats,
        "non_dealer": non_dealer_round_stats,
        "per_player": per_player_stats
    }


def simulate_table(composition, cfg, baseline_utility=None):
    """
    Simulate a full table trial with given composition using REAL Monte Carlo.
    """
    if baseline_utility is None:
        baseline_utility = cfg.get("baseline_utility", 50)
    
    num_def = composition
    num_agg = 4 - composition

    players = []
    fan_min = cfg["fan_min"]
    t_fan_threshold = cfg["t_fan_threshold"]

    for _ in range(num_def):
        players.append({
            "strategy": lambda f, fm=fan_min: defensive_strategy(f, fm),
            "strategy_type": "DEF"
        })
    for _ in range(num_agg):
        players.append({
            "strategy": lambda f, th=t_fan_threshold: aggressive_strategy(f, th),
            "strategy_type": "AGG"
        })

    result = _run_table(players, cfg, cfg["rounds_per_trial"], baseline_utility)
    result["composition"] = composition
    return result


def simulate_custom_table(players, cfg, rounds_per_trial=None, baseline_utility=None):
    """
    Run a table simulation with a custom list of players using REAL Monte Carlo.
    
    Args:
        players: List of player dicts with "strategy" and "strategy_type"
        cfg: Configuration dictionary
        rounds_per_trial: Number of rounds (defaults to cfg["rounds_per_trial"])
        baseline_utility: Baseline utility (defaults to cfg["baseline_utility"] or 50)
    
    Returns:
        Dictionary with aggregated statistics
    """
    if rounds_per_trial is None:
        rounds_per_trial = cfg.get("rounds_per_trial")
        if rounds_per_trial is None:
            raise ValueError("rounds_per_trial must be specified in config")
    if baseline_utility is None:
        baseline_utility = cfg.get("baseline_utility", 50)
    result = _run_table(players, cfg, rounds_per_trial, baseline_utility)
    result["composition"] = None
    return result


def run_composition_experiments(cfg, num_trials=None):
    """
    Run experiments for all table compositions (θ = 0 to 4).
    
    Args:
        cfg: Configuration dictionary
        num_trials: Number of trials per composition (defaults to cfg["trials"])
    
    Returns:
        Dictionary with results for each composition
    """
    if num_trials is None:
        num_trials = cfg.get("trials")
        if num_trials is None:
            raise ValueError("trials must be specified in config")
    
    compositions = [0, 1, 2, 3, 4]  # θ = number of DEF players
    results = {}
    
    for composition in compositions:
        print(f"Running composition θ={composition} ({composition} DEF, {4-composition} AGG)...")
        
        all_def_profits = []
        all_def_utilities = []
        all_agg_profits = []
        all_agg_utilities = []
        all_def_win_rates = []
        all_agg_win_rates = []
        all_def_deal_in_rates = []
        all_agg_deal_in_rates = []
        all_def_missed_hu_rates = []
        all_agg_missed_hu_rates = []
        all_def_fans = []
        all_agg_fans = []
        all_dealer_profits = []
        all_dealer_utilities = []
        all_dealer_wins = []
        all_dealer_deal_in_rates = []
        all_dealer_deal_in_loss_rates = []
        all_dealer_missed_hu = []
        all_dealer_fans = []
        all_non_dealer_profits = []
        all_non_dealer_utilities = []
        all_non_dealer_wins = []
        all_non_dealer_deal_in_rates = []
        all_non_dealer_deal_in_loss_rates = []
        all_non_dealer_missed_hu = []
        all_non_dealer_fans = []
        
        for _ in range(num_trials):
            trial_result = simulate_table(composition, cfg)
            
            if len(trial_result["defensive"]["profits"]) > 0:
                all_def_profits.extend(trial_result["defensive"]["profits"])
                all_def_utilities.extend(trial_result["defensive"]["utilities"])
                all_def_win_rates.extend(trial_result["defensive"]["wins"])
                all_def_deal_in_rates.extend(trial_result["defensive"]["deal_in_as_winner"])
                all_def_missed_hu_rates.extend(trial_result["defensive"]["missed_hu"])
                all_def_fans.extend(trial_result["defensive"]["fans"])
            
            if len(trial_result["aggressive"]["profits"]) > 0:
                all_agg_profits.extend(trial_result["aggressive"]["profits"])
                all_agg_utilities.extend(trial_result["aggressive"]["utilities"])
                all_agg_win_rates.extend(trial_result["aggressive"]["wins"])
                all_agg_deal_in_rates.extend(trial_result["aggressive"]["deal_in_as_winner"])
                all_agg_missed_hu_rates.extend(trial_result["aggressive"]["missed_hu"])
                all_agg_fans.extend(trial_result["aggressive"]["fans"])
            
            dealer_stats = trial_result["dealer"]
            non_dealer_stats = trial_result["non_dealer"]
            
            all_dealer_profits.extend(dealer_stats["profits"])
            all_dealer_utilities.extend(dealer_stats["utilities"])
            all_dealer_wins.extend(dealer_stats["wins"])
            all_dealer_deal_in_rates.extend(dealer_stats["deal_in_as_winner"])
            all_dealer_deal_in_loss_rates.extend(dealer_stats["deal_in_as_loser"])
            all_dealer_missed_hu.extend(dealer_stats["missed_hu"])
            all_dealer_fans.extend(dealer_stats["fans"])
            
            all_non_dealer_profits.extend(non_dealer_stats["profits"])
            all_non_dealer_utilities.extend(non_dealer_stats["utilities"])
            all_non_dealer_wins.extend(non_dealer_stats["wins"])
            all_non_dealer_deal_in_rates.extend(non_dealer_stats["deal_in_as_winner"])
            all_non_dealer_deal_in_loss_rates.extend(non_dealer_stats["deal_in_as_loser"])
            all_non_dealer_missed_hu.extend(non_dealer_stats["missed_hu"])
            all_non_dealer_fans.extend(non_dealer_stats["fans"])
        
        results[composition] = {
            "defensive": {
                "mean_profit": np.mean(all_def_profits) if len(all_def_profits) > 0 else 0.0,
                "std_profit": np.std(all_def_profits) if len(all_def_profits) > 0 else 0.0,
                "mean_utility": np.mean(all_def_utilities) if len(all_def_utilities) > 0 else 0.0,
                "std_utility": np.std(all_def_utilities) if len(all_def_utilities) > 0 else 0.0,
                "win_rate": np.mean(all_def_win_rates) if len(all_def_win_rates) > 0 else 0.0,
                "deal_in_rate": np.mean(all_def_deal_in_rates) if len(all_def_deal_in_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_def_missed_hu_rates) if len(all_def_missed_hu_rates) > 0 else 0.0,
                "mean_fan": np.mean(all_def_fans) if len(all_def_fans) > 0 else 0.0,
                "fan_distribution": all_def_fans
            },
            "aggressive": {
                "mean_profit": np.mean(all_agg_profits) if len(all_agg_profits) > 0 else 0.0,
                "std_profit": np.std(all_agg_profits) if len(all_agg_profits) > 0 else 0.0,
                "mean_utility": np.mean(all_agg_utilities) if len(all_agg_utilities) > 0 else 0.0,
                "std_utility": np.std(all_agg_utilities) if len(all_agg_utilities) > 0 else 0.0,
                "win_rate": np.mean(all_agg_win_rates) if len(all_agg_win_rates) > 0 else 0.0,
                "deal_in_rate": np.mean(all_agg_deal_in_rates) if len(all_agg_deal_in_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_agg_missed_hu_rates) if len(all_agg_missed_hu_rates) > 0 else 0.0,
                "mean_fan": np.mean(all_agg_fans) if len(all_agg_fans) > 0 else 0.0,
                "fan_distribution": all_agg_fans
            },
            "dealer": {
                "mean_profit": np.mean(all_dealer_profits) if len(all_dealer_profits) > 0 else 0.0,
                "std_profit": np.std(all_dealer_profits) if len(all_dealer_profits) > 0 else 0.0,
                "mean_utility": np.mean(all_dealer_utilities) if len(all_dealer_utilities) > 0 else 0.0,
                "std_utility": np.std(all_dealer_utilities) if len(all_dealer_utilities) > 0 else 0.0,
                "win_rate": np.mean(all_dealer_wins) if len(all_dealer_wins) > 0 else 0.0,
                "deal_in_rate": np.mean(all_dealer_deal_in_rates) if len(all_dealer_deal_in_rates) > 0 else 0.0,
                "deal_in_loss_rate": np.mean(all_dealer_deal_in_loss_rates) if len(all_dealer_deal_in_loss_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_dealer_missed_hu) if len(all_dealer_missed_hu) > 0 else 0.0,
                "mean_fan": np.mean([f for f in all_dealer_fans if f > 0]) if len(all_dealer_fans) > 0 else 0.0,
                "fan_distribution": all_dealer_fans
            },
            "non_dealer": {
                "mean_profit": np.mean(all_non_dealer_profits) if len(all_non_dealer_profits) > 0 else 0.0,
                "std_profit": np.std(all_non_dealer_profits) if len(all_non_dealer_profits) > 0 else 0.0,
                "mean_utility": np.mean(all_non_dealer_utilities) if len(all_non_dealer_utilities) > 0 else 0.0,
                "std_utility": np.std(all_non_dealer_utilities) if len(all_non_dealer_utilities) > 0 else 0.0,
                "win_rate": np.mean(all_non_dealer_wins) if len(all_non_dealer_wins) > 0 else 0.0,
                "deal_in_rate": np.mean(all_non_dealer_deal_in_rates) if len(all_non_dealer_deal_in_rates) > 0 else 0.0,
                "deal_in_loss_rate": np.mean(all_non_dealer_deal_in_loss_rates) if len(all_non_dealer_deal_in_loss_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_non_dealer_missed_hu) if len(all_non_dealer_missed_hu) > 0 else 0.0,
                "mean_fan": np.mean([f for f in all_non_dealer_fans if f > 0]) if len(all_non_dealer_fans) > 0 else 0.0,
                "fan_distribution": all_non_dealer_fans
            }
        }
    
    return results


# ============================================================================
# Single-Player Simulation Functions (convenience wrappers for 4-player table)
# ============================================================================
# Note: These functions are convenience wrappers that create a 4-player table
# with 1 test player + 3 neutral players. They internally use the 4-player
# table simulation functions.

def simulate_round(player_strategy: Callable[[Union[int, float]], bool], 
                  cfg: Dict[str, Any], is_dealer: bool = False) -> Dict[str, Union[float, int, bool]]:
    """
    Simulate a single round with 1 test player + 3 neutral players.
    
    This is a convenience wrapper that creates a 4-player table internally.
    All Mahjong games are 4-player; this just simplifies the interface for
    testing a single strategy.
    
    Args:
        player_strategy: Strategy function that takes fan and returns bool
        cfg: Configuration dictionary
        is_dealer: Whether test player is dealer
    
    Returns:
        Dictionary with round results for the test player only
    """
    from .players import NeutralPolicy
    
    # Determine strategy type for test player
    fan_min = cfg.get("fan_min", 1)
    fan_threshold = cfg.get("t_fan_threshold", 3)
    test_strategy_type = "DEF"  # Default
    if player_strategy(fan_min):
        test_strategy_type = "DEF"
    elif not player_strategy(fan_threshold - 1):
        test_strategy_type = "AGG"
    
    # Create 4-player table: 1 test player + 3 neutral players
    players = [
        {"strategy": player_strategy, "strategy_type": test_strategy_type},
        {"strategy": NeutralPolicy(seed=random.randint(0, 2**32-1)), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=random.randint(0, 2**32-1)), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=random.randint(0, 2**32-1)), "strategy_type": "NEU"}
    ]
    
    # Simulate one round using 4-player table simulation
    dealer_index = 0 if is_dealer else 1
    round_results, _ = simulate_table_round(players, cfg, dealer_index)
    
    # Return only the test player's (first player's) results
    return round_results[0]


def run_simulation(strategy_fn: Callable[[Union[int, float]], bool], 
                  cfg: Dict[str, Any], baseline_utility: Optional[int] = None) -> Dict[str, Any]:
    """
    Run a single trial (multiple rounds) with 1 test player + 3 neutral players.
    
    This is a convenience wrapper that uses simulate_custom_table() internally.
    All Mahjong games are 4-player; this just simplifies the interface.
    
    Args:
        strategy_fn: Strategy function
        cfg: Configuration dictionary
        baseline_utility: Baseline emotional utility at start (defaults to cfg["baseline_utility"] or 50)
    
    Returns:
        Dictionary with aggregated statistics for this trial
    """
    from .players import NeutralPolicy
    
    if baseline_utility is None:
        baseline_utility = cfg.get("baseline_utility", 50)
    
    # Determine strategy type for test player
    fan_min = cfg.get("fan_min", 1)
    fan_threshold = cfg.get("t_fan_threshold", 3)
    test_strategy_type = "DEF"  # Default
    if strategy_fn(fan_min):
        test_strategy_type = "DEF"
    elif not strategy_fn(fan_threshold - 1):
        test_strategy_type = "AGG"
    
    # Create 4-player table: 1 test player + 3 neutral players
    players = [
        {"strategy": strategy_fn, "strategy_type": test_strategy_type},
        {"strategy": NeutralPolicy(seed=random.randint(0, 2**32-1)), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=random.randint(0, 2**32-1)), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=random.randint(0, 2**32-1)), "strategy_type": "NEU"}
    ]
    
    # Use 4-player table simulation
    table_result = simulate_custom_table(players, cfg, baseline_utility=baseline_utility)
    
    # Extract test player's (first player's) statistics
    test_player_stats = table_result["per_player"][0]
    
    return {
        "profit": test_player_stats["profit"],
        "utility": test_player_stats["utility"],
        "mean_fan": test_player_stats["mean_fan"],
        "win_rate": test_player_stats["win_rate"],
        "deal_in_rate": test_player_stats["deal_in_rate"],
        "deal_in_loss_rate": test_player_stats["deal_in_loss_rate"],
        "missed_win_rate": test_player_stats["missed_win_rate"],
        "fan_distribution": test_player_stats["fan_distribution"]
    }


def run_multiple_trials(strategy_fn: Callable[[Union[int, float]], bool], 
                       cfg: Dict[str, Any], num_trials: Optional[int] = None) -> Dict[str, Any]:
    """
    Run multiple trials with 1 test player + 3 neutral players.
    
    This is a convenience wrapper that uses simulate_custom_table() internally.
    All Mahjong games are 4-player; this just simplifies the interface.
    
    Args:
        strategy_fn: Strategy function
        cfg: Configuration dictionary
        num_trials: Number of trials (defaults to cfg["trials"])
    
    Returns:
        Dictionary with aggregated statistics across all trials
    """
    if num_trials is None:
        num_trials = cfg.get("trials")
        if num_trials is None:
            raise ValueError("trials must be specified in config")
    
    all_profits = []
    all_utilities = []
    all_mean_fans = []
    all_win_rates = []
    all_deal_in_rates = []
    all_deal_in_loss_rates = []
    all_missed_win_rates = []
    all_fan_distributions = []
    
    for _ in range(num_trials):
        result = run_simulation(strategy_fn, cfg)
        all_profits.append(result["profit"])
        all_utilities.append(result["utility"])
        all_mean_fans.append(result["mean_fan"])
        all_win_rates.append(result["win_rate"])
        all_deal_in_rates.append(result["deal_in_rate"])
        all_deal_in_loss_rates.append(result["deal_in_loss_rate"])
        all_missed_win_rates.append(result["missed_win_rate"])
        all_fan_distributions.extend(result["fan_distribution"])
    
    return {
        "profits": np.array(all_profits),
        "utilities": np.array(all_utilities),
        "mean_fans": np.array(all_mean_fans),
        "win_rates": np.array(all_win_rates),
        "deal_in_rates": np.array(all_deal_in_rates),
        "deal_in_loss_rates": np.array(all_deal_in_loss_rates),
        "missed_win_rates": np.array(all_missed_win_rates),
        "fan_distribution": np.array(all_fan_distributions),
        "num_trials": num_trials
    }

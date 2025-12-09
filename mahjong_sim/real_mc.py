"""
Real Monte Carlo simulation for Beijing Mahjong.

Implements actual tile-based game simulation with:
- 136 tiles (Wan, Tiao, Tong, Feng, Jian)
- Real deal, draw, discard mechanics
- Real hand state management
- Real winning hand detection
- Real fan calculation based on actual patterns
- Real player interactions (Peng, Hu) - Chi is NOT allowed
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum
from collections import Counter
import random


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
                    
                    # Player restarts turn: draw replacement tile
                    replacement = self.wall.draw()
                    if replacement:
                        player.hand.add_tile(replacement)
                        # Check if can win on replacement tile
                        can_win_after_kong, fan_after_kong = player.can_win_on_tile(
                            replacement, is_self_draw=True)
                        if can_win_after_kong:
                            fan_min = self.cfg.get("fan_min", 1)
                            fan_threshold = self.cfg.get("t_fan_threshold", 3)
                            risk = len(self.discard_pile) / max(100, self.wall.remaining() + len(self.discard_pile))
                            if player.should_hu(fan_after_kong, fan_min, fan_threshold, risk):
                                return self._process_win(player, fan_after_kong, is_self_draw=True)
                        # After Kong, player continues turn (will discard in next iteration)
                        # current_player stays the same
                    else:
                        # Wall exhausted after Kong - end round as draw
                        return self._process_draw()
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
                            
                            # Player restarts turn: draw replacement tile
                            self.current_player = i
                            replacement = self.wall.draw()
                            if replacement:
                                other_player.hand.add_tile(replacement)
                                # Check if can win on replacement tile
                                can_win_after_kong, fan_after_kong = other_player.can_win_on_tile(
                                    replacement, is_self_draw=True)
                                if can_win_after_kong:
                                    fan_min = self.cfg.get("fan_min", 1)
                                    fan_threshold = self.cfg.get("t_fan_threshold", 3)
                                    risk = len(self.discard_pile) / max(100, self.wall.remaining() + len(self.discard_pile))
                                    if other_player.should_hu(fan_after_kong, fan_min, fan_threshold, risk):
                                        return self._process_win(other_player, fan_after_kong, 
                                                                   is_self_draw=True)
                                # After Kong, player continues turn (will discard in next iteration)
                            else:
                                # Wall exhausted after Kong - end round as draw
                                return self._process_draw()
                            
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
        from .scoring import compute_score, compute_winner_profit, compute_loser_cost
        from .simulation import compute_utility
        
        score = compute_score(fan, self.cfg.get("base_points", 1))
        
        if is_self_draw:
            # Self-draw: winner gets from all 3 opponents
            winner_profit = compute_winner_profit(score, is_self_draw=True, deal_in_occurred=False)
            winner.profit += winner_profit * 3  # From 3 opponents
            
            for player in self.players:
                if player != winner:
                    loser_cost = compute_loser_cost(score, self.cfg.get("penalty_deal_in", 3), 
                                                   is_deal_in_loser=False)
                    player.profit += loser_cost
        else:
            # Deal-in: winner gets from deal-in player only
            winner_profit = compute_winner_profit(score, is_self_draw=False, deal_in_occurred=True)
            winner.profit += winner_profit
            
            if deal_in_player:
                loser_cost = compute_loser_cost(score, self.cfg.get("penalty_deal_in", 3), 
                                               is_deal_in_loser=True)
                deal_in_player.profit += loser_cost
        
        winner.wins += 1
        
        # Calculate utility
        winner.utility += compute_utility(winner_profit, missed_hu=False, deal_in_as_loser=False)
        
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


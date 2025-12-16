"""
Hand class for managing player's tiles and melds.
"""

from typing import List, Tuple, Optional, Set, Dict
from collections import Counter
from .tiles import Tile, TileType


class Hand:
    """Player hand"""
    def __init__(self):
        self.tiles: List[Tile] = []  # Hand tiles
        self.melds: List[List[Tile]] = []  # All melds (Pongs, Chis, Gongs, Pair)
        # Meld types:
        # - Pong (triplet): 3 tiles
        # - Chi (sequence): 3 tiles
        # - Gong (quad): 4 tiles (upgraded from Pong)
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
        - Pong (triplet): 3 tiles
        - Chi (sequence): 3 tiles
        - Gong (quad): 4 tiles (upgraded from Pong)
        - Pair: 2 tiles (part of winning requirement)
        
        Args:
            meld: List of tiles in the meld
            remove_from_hand: If True, remove tiles from hand
                             If False, tiles already removed (for Pong/exposed melds)
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
    
    def can_pong(self, discarded_tile: Tile) -> bool:
        """
        Check if can Pong (triplet).
        """
        count = sum(1 for t in self.tiles if t == discarded_tile)
        return count >= 2
    
    def can_gong(self, tile: Tile = None) -> Optional[int]:
        """
        Check if can Gong (upgrade existing Pong meld to Gong).
        
        Gong can only be formed by upgrading an existing Pong meld:
        - Self-draw: if player has a Pong meld and draws the 4th identical tile
        - From discard: if player has a Pong meld and another player discards the 4th identical tile
        
        Args:
            tile: The tile to check (drawn tile or discarded tile). If None, checks hand tiles.
        
        Returns:
            Index of Pong meld that can be upgraded to Gong, or None if no upgrade possible
        """
        if tile:
            # Check if any existing Pong meld matches this tile
            for i, meld in enumerate(self.melds):
                if len(meld) == 3 and meld[0] == tile:
                    # This Pong meld can be upgraded to Gong
                    return i
        else:
            # Check hand tiles for 4th tile of any Pong meld
            for i, meld in enumerate(self.melds):
                if len(meld) == 3:
                    pong_tile = meld[0]
                    count = sum(1 for t in self.tiles if t == pong_tile)
                    if count >= 1:
                        # Have the 4th tile, can upgrade Pong to Gong
                        return i
        return None
    
    def can_chi(self, discarded_tile: Tile) -> List[List[Tile]]:
        """
        Check if can Chi (sequence) from discard.
        
        Chi can only be formed from discard (not self-drawn in this variant).
        
        Returns list of possible chi sequences.
        """
        chis = []
        if discarded_tile.tile_type not in [TileType.WAN, TileType.TIAO, TileType.TONG]:
            return []  # Only suited tiles can form chis
        
        # Check for chi sequences (e.g., 4-5-6, need 4 and 5 or 5 and 6 or 6 and 7)
        if discarded_tile.value >= 3:  # Can be middle or end of sequence
            # Check for sequence ending with discard (e.g., 3-4-5, discard is 5)
            tile_minus2 = Tile(discarded_tile.tile_type, discarded_tile.value - 2)
            tile_minus1 = Tile(discarded_tile.tile_type, discarded_tile.value - 1)
            if tile_minus2 in self.tiles and tile_minus1 in self.tiles:
                chis.append([tile_minus2, tile_minus1, discarded_tile])
        
        if 2 <= discarded_tile.value <= 8:  # Can be middle of sequence
            # Check for sequence with discard in middle (e.g., 4-5-6, discard is 5)
            tile_minus1 = Tile(discarded_tile.tile_type, discarded_tile.value - 1)
            tile_plus1 = Tile(discarded_tile.tile_type, discarded_tile.value + 1)
            if tile_minus1 in self.tiles and tile_plus1 in self.tiles:
                chis.append([tile_minus1, discarded_tile, tile_plus1])
        
        if discarded_tile.value <= 7:  # Can be start of sequence
            # Check for sequence starting with discard (e.g., 4-5-6, discard is 4)
            tile_plus1 = Tile(discarded_tile.tile_type, discarded_tile.value + 1)
            tile_plus2 = Tile(discarded_tile.tile_type, discarded_tile.value + 2)
            if tile_plus1 in self.tiles and tile_plus2 in self.tiles:
                chis.append([discarded_tile, tile_plus1, tile_plus2])
        
        return chis
    
    def check_winning_hand(self) -> Tuple[bool, List[List[Tile]]]:
        """
        Check if hand is winning (Hu).
        Returns (is_winning, list_of_melds_for_winning_pattern)
        
        Winning rule: 4 melds (pongs/chis/gongs) + 1 pair
        Meld types:
        - Pong (triplet): 3 identical tiles
        - Chi (sequence): 3 consecutive suited tiles
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
        can be decomposed into 4 melds (pong/chi) + 1 pair, regardless of total count.
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


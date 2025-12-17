"""
Fan (points) calculation for winning Mahjong hands.
"""

from typing import List, Tuple
from collections import Counter
from .tiles import Tile, TileType
from .hand import Hand


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
        
        # (1) Self-draw — 1 fan
        if is_self_draw:
            fan += 1
        
        # (2) Concealed hand — 1 fan
        # No exposed melds (all melds are concealed)
        # For concealed hand, we check if there are any melds at all
        # Actually, if melds exist, they are exposed (Pong from discard)
        # So concealed hand means no melds
        if len(hand.melds) == 0:
            fan += 1
        
        # (3) All simples — 1 fan
        # No terminals (1 or 9) and no honors
        if FanCalculator._is_all_simples(all_tiles):
            fan += 1
        
        # ===== 2. Common Wins — 2 Fan Each =====
        
        # (4) All pongs — 2 fan
        # Hand consists of four pong sets and one pair
        if len(triplets) == 4 and len(sequences) == 0:
            fan += 2
        
        # (5) Mixed triple chi — 2 fan
        # Same numbered chi appears in all three suits
        if FanCalculator._has_mixed_triple_chi(hand, winning_melds):
            fan += 2
        
        # ===== 3. Advanced Hands — 4–6 Fan Each =====
        
        # (6) Pure flush — 4–6 fan
        # Whole hand uses tiles from one suit, no honors
        pure_flush_result = FanCalculator._is_pure_flush(all_tiles, len(hand.melds) == 0)
        if pure_flush_result:
            fan += pure_flush_result  # 4 fan if exposed, 6 fan if concealed
        
        # (7) Little dragons — 4–6 fan
        # Two dragon pongs + pair made from the remaining dragon
        little_dragons_result = FanCalculator._is_little_dragons(hand, winning_melds)
        if little_dragons_result:
            fan += little_dragons_result  # 4 fan if exposed, 6 fan if concealed
        
        # ===== 4. Add-on Bonuses — +1 to +2 Fan =====
        
        # (8) Gong — +1 fan per gong
        # Count gongs (4-tile melds)
        # Gongs can be in hand.melds (exposed) or in winning_melds (concealed from hand tiles)
        gong_count = 0
        # Count exposed gongs (in hand.melds)
        for meld in hand.melds:
            if len(meld) == 4:
                gong_count += 1
        # Count concealed gongs (in winning_melds but not in hand.melds)
        # A gong in winning_melds is concealed if it's not already in hand.melds
        for meld in winning_melds:
            if len(meld) == 4:
                # Check if this gong is already counted in hand.melds
                is_already_counted = False
                for exposed_meld in hand.melds:
                    if len(exposed_meld) == 4 and exposed_meld[0] == meld[0]:
                        is_already_counted = True
                        break
                if not is_already_counted:
                    gong_count += 1
        fan += gong_count  # +1 fan per gong
        
        # (9) "Gong open" win — +1 fan
        # This is handled by checking if the winning tile was drawn after a gong
        # For now, we don't track this in the current implementation
        # (would need to pass a flag indicating if this is a "gong open" win)
        
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
    def _has_mixed_triple_chi(hand: Hand, winning_melds: List[List[Tile]]) -> bool:
        """
        Check if hand has mixed triple chi (same numbered chi in all three suits).
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
        Check if hand is little dragons (two dragon pongs + pair of third dragon).
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


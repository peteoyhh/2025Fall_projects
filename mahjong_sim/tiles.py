"""
Tile-related classes for Mahjong game.
"""

from typing import List, Optional
from enum import Enum
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


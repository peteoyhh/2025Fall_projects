"""
Real Monte Carlo simulation for Beijing Mahjong.

This is the unified simulation module that combines:
- Core game mechanics (tiles, hands, players)
- Table simulation (4-player games)
- Single-player simulation
- All experiment interfaces

All simulation uses actual tile-based gameplay with 136 tiles.
We used AI-assisted tools (OpenAI ChatGPT) to support text refinement, structural organization, 
and grammar editing during manuscript preparation. AI tools were not used for generating research ideas, 
analyzing data, conducting experiments, or drawing conclusions. All methodological decisions, analytical 
results, and interpretations were fully developed and validated by the authors
"""


import numpy as np
from typing import List, Dict, Tuple, Optional, Callable, Union, Any
import random
import time

# Import scoring functions
from .scoring import (
    compute_score,
    compute_winner_profit,
    compute_loser_cost
)
from .strategies import defensive_strategy, aggressive_strategy, BaseStrategy, TableState, TempoDefender, ValueChaser
from .tiles import Tile, TileType, TileWall
from .hand import Hand
from .fan_calculator import FanCalculator




# ============================================================================
# Core Game Classes
# ============================================================================
# Note: Tile, TileType, TileWall are now in tiles.py
#       Hand is now in hand.py
#       FanCalculator is now in fan_calculator.py


class Player:
    """Mahjong player"""
    def __init__(self, player_id: int, strategy_type: str, strategy_fn=None, cfg=None):
        self.player_id = player_id
        self.strategy_type = strategy_type  # "DEF" or "AGG" or custom
        self.strategy_fn = strategy_fn
        self.strategy_impl = strategy_fn if isinstance(strategy_fn, BaseStrategy) else None
        self.cfg = cfg or {}
        self.hand = Hand()
        self.is_dealer = False
        self.profit = 0.0
        self.wins = 0
        self.deal_ins = 0
        self.missed_hus = 0
    
    def should_hu(self, fan: int, fan_min: int = 1, fan_threshold: int = 3, risk: float = 0.0) -> bool:
        """Strategy decision: should declare Hu?"""
        if self.strategy_impl:
            return self.strategy_impl.should_hu(fan, risk, self.hand, fan_min, fan_threshold)
        if hasattr(self.strategy_fn, "should_hu"):
            return self.strategy_fn.should_hu(fan, risk)
        if self.strategy_type == "DEF":
            return fan >= fan_min
        elif self.strategy_type == "AGG":
            return fan >= fan_threshold
        elif self.strategy_type == "NEU":
            # Neutral policy fallback (should rarely be used if NeutralPolicy object is provided)
            strategy_cfg = self.cfg.get("strategy_thresholds", {})
            neutral_thresholds = strategy_cfg.get("neutral_policy", {})
            target_fan = neutral_thresholds.get("target_fan", 3)
            medium_risk = neutral_thresholds.get("medium_risk_threshold", 0.45)
            bailout_risk = neutral_thresholds.get("bailout_risk_threshold", 0.70)
            # High risk: risk >= 0.70, accept fan >= 1
            if risk >= bailout_risk:
                return fan >= 1
            # Medium risk: 0.45 <= risk < 0.70, accept fan >= 2
            if risk >= medium_risk and risk < bailout_risk:
                return fan >= 2
            # Low risk: risk < 0.45, pursue target fan (fan >= 3)
            return fan >= target_fan
        elif callable(self.strategy_fn):
            return self.strategy_fn(fan)
        return fan >= 1

    def should_claim(self, action: str, context: dict) -> bool:
        """Decide whether to claim discard for gong/pong/chi."""
        if self.strategy_impl:
            return self.strategy_impl.decide_claim(action, context)
        # Neutral/simple fallback: always take Pong/Gong, Chi only if low risk
        # Use ValueChaser chi threshold as fallback (should rarely be used)
        risk = context.get("risk", 0.0)
        strategy_cfg = self.cfg.get("strategy_thresholds", {})
        value_thresholds = strategy_cfg.get("value_chaser", {})
        chi_risk_threshold = value_thresholds.get("chi_risk_threshold", 0.7)
        if action in ("pong", "gong"):
            return True
        if action == "chi":
            return risk < chi_risk_threshold
        return True
    
    def decide_discard(self, table_state: Optional[TableState] = None) -> Optional[Tile]:
        """Decide which tile to discard"""
        if not self.hand.tiles:
            return None
        if self.strategy_impl:
            return self.strategy_impl.choose_discard(self.hand, table_state or TableState([], 0, 0, 0.0, None, 0))
        # Simple strategy: discard first tile
        return self.hand.tiles[0]
    
    def can_win_on_tile(self, tile: Tile, is_self_draw: bool = False) -> Tuple[bool, int]:
        """Check if can win with this tile, return (can_win, fan)"""
        # Check if tile is already in hand
        tile_already_in_hand = tile in self.hand.tiles
        
        # Add tile temporarily (if not already in hand)
        if not tile_already_in_hand:
            self.hand.add_tile(tile)
        
        can_win, _ = self.hand.check_winning_hand()
        
        if can_win:
            # Calculate fan
            fan = FanCalculator.calculate_fan(self.hand, is_self_draw=is_self_draw, 
                                             is_dealer=self.is_dealer)
            # Remove tile only if we added it
            if not tile_already_in_hand:
                self.hand.remove_tile(tile)
            return True, fan
        else:
            # Remove tile only if we added it
            if not tile_already_in_hand:
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
        # Get risk calculation parameter from config
        risk_cfg = cfg.get("risk_calculation", {})
        self.risk_max_denominator = risk_cfg.get("max_denominator", 100)
    
    def _calculate_risk(self) -> float:
        """Calculate risk based on discard pile size and wall remaining"""
        return len(self.discard_pile) / max(self.risk_max_denominator, 
                                            self.wall.remaining() + len(self.discard_pile))
    
    def initialize_round(self, players: List[Player], dealer_index: int = 0):
        """Initialize a new round"""
        self.wall = TileWall()
        self.players = players
        self.current_player = dealer_index
        self.discard_pile = []
        self.round_results = []
        # Track opponent discards by suit for strategy analysis
        self.opponent_discards_by_player = {i: [] for i in range(len(players))}
        
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
            # Base risk estimate for this turn (used across decisions)
            risk = self._calculate_risk()
            
            # Build opponent discard information for strategy analysis
            opponent_discards_by_suit = {}
            for i, other_player in enumerate(self.players):
                if i != self.current_player:
                    player_discards = self.opponent_discards_by_player[i]
                    for discarded_tile in player_discards:
                        suit = discarded_tile.tile_type
                        if suit not in opponent_discards_by_suit:
                            opponent_discards_by_suit[suit] = []
                        opponent_discards_by_suit[suit].append(discarded_tile)
            
            # Check if win FIRST (after draw)
            can_win, fan = player.can_win_on_tile(drawn_tile, is_self_draw=True)
            
            if can_win:
                # Strategy decision
                fan_min = self.cfg.get("fan_min", 1)
                fan_threshold = self.cfg.get("t_fan_threshold", 3)
                # Estimate risk (simplified: based on discard pile size)
                risk = self._calculate_risk()
                table_state = TableState(
                    discard_pile=self.discard_pile,
                    wall_remaining=self.wall.remaining(),
                    turn=turn,
                    risk=risk,
                    opponent_discards_by_suit=opponent_discards_by_suit,
                    total_tiles_discarded=len(self.discard_pile)
                )
                
                if player.should_hu(fan, fan_min, fan_threshold, risk):
                    # Player wins!
                    return self._process_win(player, fan, is_self_draw=True)
                else:
                    # Missed Hu opportunity
                    player.missed_hus += 1
            
            # If not win, check for Gong (upgrade existing Pong meld)
            # Gong can only be formed by upgrading an existing Pong meld
            gong_meld_idx = player.hand.can_gong(drawn_tile)
            if gong_meld_idx is not None and 0 <= gong_meld_idx < len(player.hand.melds):
                # Upgrade existing Pong meld to Gong
                old_pong = player.hand.melds[gong_meld_idx]
                # Remove the 4th tile from hand (drawn_tile)
                if player.hand.remove_tile(drawn_tile):
                    # Replace Pong with Gong (4 tiles)
                    gong_meld = old_pong.copy() + [drawn_tile]
                    player.hand.melds[gong_meld_idx] = gong_meld
                    # Gong is a fixed meld (no special marking needed)
                    
                    # Player restarts turn: continuously check for Gong and win after drawing replacement tiles
                    while True:
                        replacement = self.wall.draw()
                        if not replacement:
                            # Wall exhausted after Gong - end round as draw
                            return self._process_draw()
                        
                        player.hand.add_tile(replacement)
                        
                        # Check if can win on replacement tile FIRST
                        can_win_after_gong, fan_after_gong = player.can_win_on_tile(
                            replacement, is_self_draw=True)
                        if can_win_after_gong:
                            fan_min = self.cfg.get("fan_min", 1)
                            fan_threshold = self.cfg.get("t_fan_threshold", 3)
                            risk = self._calculate_risk()
                            if player.should_hu(fan_after_gong, fan_min, fan_threshold, risk):
                                return self._process_win(player, fan_after_gong, is_self_draw=True)
                        
                        # Check if can Gong again (upgrade another Pong meld)
                        gong_meld_idx = player.hand.can_gong(replacement)
                        if gong_meld_idx is not None and 0 <= gong_meld_idx < len(player.hand.melds):
                            # Upgrade another Pong meld to Gong
                            old_pong = player.hand.melds[gong_meld_idx]
                            if player.hand.remove_tile(replacement):
                                gong_meld = old_pong.copy() + [replacement]
                                player.hand.melds[gong_meld_idx] = gong_meld
                                # Continue loop to draw another replacement tile
                                continue
                            else:
                                # Should not happen, but if remove fails, replacement tile stays in hand
                                # Break and continue to discard (replacement tile will be discarded)
                                break
                        else:
                            # No more Gong possible, break and continue to discard
                            break
                    # After Gong(s), player continues turn
                    # The while loop (Gong replacement tiles) completes, then breaks to discard logic
                    # current_player stays the same, so in the next while turn iteration, this player will discard
                # If remove_tile failed, drawn_tile is still in hand, skip Gong and continue normally
                # (drawn_tile will be discarded later)
            else:
                # If no Gong, check for self-draw Pong
                # If player self-draws and has 3 identical tiles, can form pong
                tile_counts = player.hand.get_tile_counts()
                for tile, count in tile_counts.items():
                    if count == 3:
                        # Can form self-draw pong
                        pong_tiles = [t for t in player.hand.tiles if t == tile]
                        # Remove 3 tiles from hand
                        removed_count = 0
                        for _ in range(3):
                            if player.hand.remove_tile(tile):
                                removed_count += 1
                            else:
                                # If remove fails, restore removed tiles and skip this pong
                                for _ in range(removed_count):
                                    player.hand.add_tile(tile)
                                break
                        
                        # Only add meld if all 3 tiles were successfully removed
                        if removed_count == 3:
                            # Add pong meld
                            player.hand.add_meld(pong_tiles, remove_from_hand=False, 
                                               is_concealed=False)
                            
                            # After self-draw pong, check if hand is now winning
                            # Check if current hand (with melds) is winning
                            # drawn_tile is still in hand if it wasn't part of the pong
                            # If drawn_tile was part of pong, it's now in the meld, so check current hand
                            can_win_after_pong, fan_after_pong = player.can_win_on_tile(
                                drawn_tile, is_self_draw=True)
                            # Note: can_win_on_tile temporarily adds the tile, so it works even if
                            # drawn_tile was already removed (part of pong) or still in hand
                            if can_win_after_pong:
                                fan_min = self.cfg.get("fan_min", 1)
                                fan_threshold = self.cfg.get("t_fan_threshold", 3)
                                risk = self._calculate_risk()
                                if player.should_hu(fan_after_pong, fan_min, fan_threshold, risk):
                                    return self._process_win(player, fan_after_pong, is_self_draw=True)
                            
                            # After self-draw pong, continue to discard
                            break  # Only form one pong at a time
                        else:
                            # Failed to remove all tiles, skip this pong and try next tile
                            continue
            
            # Note: Chi (sequence) can only be formed from discard, not self-drawn
            # So we don't check for self-draw chi here
            
            # Discard tile
            # Build opponent discard information for strategy analysis
            opponent_discards_by_suit = {}
            for i, other_player in enumerate(self.players):
                if i != self.current_player:
                    player_discards = self.opponent_discards_by_player[i]
                    for discarded_tile in player_discards:
                        suit = discarded_tile.tile_type
                        if suit not in opponent_discards_by_suit:
                            opponent_discards_by_suit[suit] = []
                        opponent_discards_by_suit[suit].append(discarded_tile)
            
            table_state = TableState(
                discard_pile=self.discard_pile,
                wall_remaining=self.wall.remaining(),
                turn=turn,
                risk=risk,
                opponent_discards_by_suit=opponent_discards_by_suit,
                total_tiles_discarded=len(self.discard_pile)
            )
            discard = player.decide_discard(table_state)
            if discard:
                player.hand.remove_tile(discard)
                self.discard_pile.append(discard)
                # Track this player's discard for opponent analysis
                self.opponent_discards_by_player[self.current_player].append(discard)
                
                table_state = TableState(
                    discard_pile=self.discard_pile,
                    wall_remaining=self.wall.remaining(),
                    turn=turn,
                    risk=risk,
                    opponent_discards_by_suit=opponent_discards_by_suit,
                    total_tiles_discarded=len(self.discard_pile)
                )
                
                # Check other players' reactions in priority order: Hu > Gong > Pong > Chi
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
                        risk = self._calculate_risk()
                        # Build opponent discard info for this check
                        opponent_discards_by_suit_check = {}
                        for j, p in enumerate(self.players):
                            if j != i:
                                player_discards = self.opponent_discards_by_player[j]
                                for discarded_tile in player_discards:
                                    suit = discarded_tile.tile_type
                                    if suit not in opponent_discards_by_suit_check:
                                        opponent_discards_by_suit_check[suit] = []
                                    opponent_discards_by_suit_check[suit].append(discarded_tile)
                        table_state = TableState(
                            discard_pile=self.discard_pile,
                            wall_remaining=self.wall.remaining(),
                            turn=turn,
                            risk=risk,
                            opponent_discards_by_suit=opponent_discards_by_suit_check,
                            total_tiles_discarded=len(self.discard_pile)
                        )
                        if other_player.should_hu(fan_other, fan_min, fan_threshold, risk):
                            # Other player wins via deal-in
                            # Remove discard from discard_pile (it's being claimed for win)
                            if discard in self.discard_pile:
                                self.discard_pile.remove(discard)
                            other_player.deal_ins += 1
                            return self._process_win(other_player, fan_other, 
                                                   is_self_draw=False, 
                                                   deal_in_player=player)
                
                # Priority 2: Check for Gong (upgrade existing Pong meld)
                if not action_taken:
                    for i in player_order:
                        other_player = self.players[i]
                        gong_meld_idx = other_player.hand.can_gong(discard)
                        if gong_meld_idx is not None and 0 <= gong_meld_idx < len(other_player.hand.melds):
                            risk_local = self._calculate_risk()
                            # Build opponent discard info
                            opponent_discards_by_suit_local = {}
                            for j, p in enumerate(self.players):
                                if j != i:
                                    player_discards = self.opponent_discards_by_player[j]
                                    for discarded_tile in player_discards:
                                        suit = discarded_tile.tile_type
                                        if suit not in opponent_discards_by_suit_local:
                                            opponent_discards_by_suit_local[suit] = []
                                        opponent_discards_by_suit_local[suit].append(discarded_tile)
                            table_state_local = TableState(
                                discard_pile=self.discard_pile,
                                wall_remaining=self.wall.remaining(),
                                turn=turn,
                                risk=risk_local,
                                opponent_discards_by_suit=opponent_discards_by_suit_local,
                                total_tiles_discarded=len(self.discard_pile)
                            )
                            if not other_player.should_claim("gong", {"risk": risk_local, "table_state": table_state_local, "fan": 0}):
                                continue
                            # Upgrade existing Pong meld to Gong
                            old_pong = other_player.hand.melds[gong_meld_idx]
                            # Replace Pong with Gong (4 tiles: 3 from meld + discard)
                            gong_meld = old_pong.copy() + [discard]
                            other_player.hand.melds[gong_meld_idx] = gong_meld
                            # Remove discard from discard_pile (it's being claimed for Gong)
                            if discard in self.discard_pile:
                                self.discard_pile.remove(discard)
                            # Gong is a fixed meld
                            
                            # Player restarts turn: continuously check for Gong and win after drawing replacement tiles
                            self.current_player = i
                            while True:
                                replacement = self.wall.draw()
                                if not replacement:
                                    # Wall exhausted after Gong - end round as draw
                                    return self._process_draw()
                                
                                other_player.hand.add_tile(replacement)
                                
                                # Check if can win on replacement tile FIRST
                                can_win_after_gong, fan_after_gong = other_player.can_win_on_tile(
                                    replacement, is_self_draw=True)
                                if can_win_after_gong:
                                    fan_min = self.cfg.get("fan_min", 1)
                                    fan_threshold = self.cfg.get("t_fan_threshold", 3)
                                    risk = self._calculate_risk()
                                    if other_player.should_hu(fan_after_gong, fan_min, fan_threshold, risk):
                                        return self._process_win(other_player, fan_after_gong, 
                                                                   is_self_draw=True)
                                
                                # Check if can Gong again (upgrade another Pong meld)
                                gong_meld_idx = other_player.hand.can_gong(replacement)
                                if gong_meld_idx is not None and 0 <= gong_meld_idx < len(other_player.hand.melds):
                                    # Upgrade another Pong meld to Gong
                                    old_pong = other_player.hand.melds[gong_meld_idx]
                                    if other_player.hand.remove_tile(replacement):
                                        gong_meld = old_pong.copy() + [replacement]
                                        other_player.hand.melds[gong_meld_idx] = gong_meld
                                        # Continue loop to draw another replacement tile
                                        continue
                                    else:
                                        # Should not happen, but if remove fails, replacement tile stays in hand
                                        # Break and continue to discard (replacement tile will be discarded)
                                        break
                                else:
                                    # No more Gong possible, break and continue to discard
                                    break
                            # After Gong(s), player continues turn
                            # Break out of player_order loop and action_taken prevents moving to next player
                            # In the next while loop iteration, this player (now current_player) will discard
                            action_taken = True
                            break  # Only one player can Gong
                
                # Priority 3: Check for Pong (triplet) or Chi (sequence)
                if not action_taken:
                    for i in player_order:
                        other_player = self.players[i]
                        # Check for Pong first
                        if other_player.hand.can_pong(discard):
                            risk_local = self._calculate_risk()
                            # Build opponent discard info
                            opponent_discards_by_suit_local = {}
                            for j, p in enumerate(self.players):
                                if j != i:
                                    player_discards = self.opponent_discards_by_player[j]
                                    for discarded_tile in player_discards:
                                        suit = discarded_tile.tile_type
                                        if suit not in opponent_discards_by_suit_local:
                                            opponent_discards_by_suit_local[suit] = []
                                        opponent_discards_by_suit_local[suit].append(discarded_tile)
                            table_state_local = TableState(
                                discard_pile=self.discard_pile,
                                wall_remaining=self.wall.remaining(),
                                turn=turn,
                                risk=risk_local,
                                opponent_discards_by_suit=opponent_discards_by_suit_local,
                                total_tiles_discarded=len(self.discard_pile)
                            )
                            if other_player.should_claim("pong", {"risk": risk_local, "table_state": table_state_local, "fan": 0}):
                                # Player does Pong from discard
                                # Remove 2 tiles from hand
                                removed_count = 0
                                for _ in range(2):
                                    if other_player.hand.remove_tile(discard):
                                        removed_count += 1
                                    else:
                                        # If remove fails, restore removed tiles and skip this pong
                                        for _ in range(removed_count):
                                            other_player.hand.add_tile(discard)
                                        break
                                
                                # Only add meld if all tiles were successfully removed
                                if removed_count == 2:
                                    # Add exposed Pong (triplet) from discard
                                    pong_meld = [discard, discard, discard]
                                    other_player.hand.add_meld(pong_meld, remove_from_hand=False, 
                                                              is_concealed=False)
                                    # Remove discard from discard_pile (it's being claimed for Pong)
                                    if discard in self.discard_pile:
                                        self.discard_pile.remove(discard)
                                    
                                    # Player who did Pong continues
                                    # action_taken prevents moving to next player, so this player will discard in next turn iteration
                                    self.current_player = i
                                    action_taken = True
                                    break  # Only one player can Pong
                                else:
                                    # Failed to remove all tiles, skip this pong and try next player
                                    continue
                        # Check for Chi (sequence)
                        elif other_player.hand.can_chi(discard):
                            # Player does Chi from discard
                            chis = other_player.hand.can_chi(discard)
                            if chis:
                                risk_local = self._calculate_risk()
                                # Build opponent discard info
                                opponent_discards_by_suit_local = {}
                                for j, p in enumerate(self.players):
                                    if j != i:
                                        player_discards = self.opponent_discards_by_player[j]
                                        for discarded_tile in player_discards:
                                            suit = discarded_tile.tile_type
                                            if suit not in opponent_discards_by_suit_local:
                                                opponent_discards_by_suit_local[suit] = []
                                            opponent_discards_by_suit_local[suit].append(discarded_tile)
                                table_state_local = TableState(
                                    discard_pile=self.discard_pile,
                                    wall_remaining=self.wall.remaining(),
                                    turn=turn,
                                    risk=risk_local,
                                    opponent_discards_by_suit=opponent_discards_by_suit_local,
                                    total_tiles_discarded=len(self.discard_pile)
                                )
                                if not other_player.should_claim("chi", {"risk": risk_local, "table_state": table_state_local, "fan": 0, "meld_options": chis}):
                                    pass
                                else:
                                    chi_meld = chis[0]
                                    # Remove 2 tiles from hand (discard is the 3rd)
                                    removed_count = 0
                                    tiles_to_remove = [t for t in chi_meld if t != discard]
                                    removed_tiles = []  # Track which tiles were successfully removed
                                    for tile in tiles_to_remove:
                                        if other_player.hand.remove_tile(tile):
                                            removed_count += 1
                                            removed_tiles.append(tile)
                                        else:
                                            # If remove fails, restore removed tiles and skip this chi
                                            for restored_tile in removed_tiles:
                                                other_player.hand.add_tile(restored_tile)
                                            break
                                    
                                    # Only add meld if all tiles were successfully removed
                                    if removed_count == len(tiles_to_remove):
                                        # Add exposed Chi (sequence) from discard
                                        other_player.hand.add_meld(chi_meld, remove_from_hand=False, 
                                                                  is_concealed=False)
                                        # Remove discard from discard_pile (it's being claimed for Chi)
                                        if discard in self.discard_pile:
                                            self.discard_pile.remove(discard)
                                        
                                        # Player who did Chi continues
                                        # action_taken prevents moving to next player, so this player will discard in next turn iteration
                                        self.current_player = i
                                        action_taken = True
                                        break  # Only one player can Chi
                                    else:
                                        # Failed to remove all tiles, skip this chi and try next player
                                        continue
                
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
        
        penalty_multiplier = self.cfg.get("penalty_deal_in", 1)
        
        if is_self_draw:
            # Self-draw: winner gets from all 3 opponents
            # compute_winner_profit already returns score * 3 for self-draw
            winner_profit = compute_winner_profit(score, is_self_draw=True, deal_in_occurred=False)
            total_winner_profit = winner_profit  # Already includes all 3 opponents
            winner.profit += total_winner_profit
            
            for player in self.players:
                if player != winner:
                    loser_cost = compute_loser_cost(score, penalty_multiplier, 
                                                   is_deal_in_loser=False)
                    player.profit += loser_cost
        else:
            # Deal-in: winner gets from deal-in player only
            # Equal transfer: winner gets score * penalty_multiplier, loser pays score * penalty_multiplier
            winner_profit = compute_winner_profit(score, is_self_draw=False, deal_in_occurred=True,
                                                 penalty_multiplier=penalty_multiplier)
            total_winner_profit = winner_profit  # Total profit (score * penalty_multiplier for deal-in)
            winner.profit += total_winner_profit
            
            if deal_in_player:
                loser_cost = compute_loser_cost(score, penalty_multiplier, 
                                               is_deal_in_loser=True)
                deal_in_player.profit += loser_cost
        
        winner.wins += 1
        
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
            # Validate winner_idx to prevent IndexError
            if 0 <= winner_idx < len(players) and players[winner_idx].is_dealer:
                # Dealer continues
                dealer_index = winner_idx
            else:
                # Rotate dealer (either winner_idx invalid or non-dealer won)
                dealer_index = (dealer_index + 1) % len(players)
        else:
            # Draw: rotate dealer
            dealer_index = (dealer_index + 1) % len(players)
    
    # Aggregate results
    results = {}
    for player in players:
        results[player.player_id] = {
            "profit": player.profit,
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
        
        mc_player = Player(i, strategy_type, strategy_fn, cfg)
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
            "fan": 0,
            "won": False,
            "deal_in_as_winner": False,
            "deal_in_as_loser": False,
            "missed_hu": False
        })
    
    if winner_idx is not None:
        # Someone won
        # _process_win has already updated all players' profit
        # So we should use player.profit directly from mc_players
        for i, player in enumerate(mc_players):
            results[i]["profit"] = player.profit
        
        winner = mc_players[winner_idx]
        results[winner_idx]["won"] = True
        results[winner_idx]["fan"] = fan
        results[winner_idx]["deal_in_as_winner"] = not is_self_draw
        
        # Set deal_in_as_loser flag for deal-in case
        if not is_self_draw:
            deal_in_player_idx = result.get("deal_in_player_id")
            if deal_in_player_idx is not None:
                results[deal_in_player_idx]["deal_in_as_loser"] = True
        
        # Check for missed Hu opportunities
        for i, player in enumerate(mc_players):
            if i != winner_idx and player.missed_hus > 0:
                results[i]["missed_hu"] = True
    
    # Round metadata
    round_meta = {
        "winner_index": winner_idx,
        "winner_is_dealer": winner_idx == dealer_index if winner_idx is not None else False,
        "dealer_ready": False,  # Not used in real MC
        "dealer_continues": winner_idx == dealer_index if winner_idx is not None else False,
        "is_draw": winner_idx is None
    }
    
    return results, round_meta


def _run_table(players, cfg, rounds_per_trial):
    """Run table simulation with multiple rounds"""
    dealer_index = 0

    player_count = len(players)

    all_profits = [[] for _ in range(player_count)]
    all_fans = [[] for _ in range(player_count)]
    all_wins = [[] for _ in range(player_count)]
    all_deal_in_as_winner = [[] for _ in range(player_count)]
    all_deal_in_as_loser = [[] for _ in range(player_count)]
    all_missed_hu = [[] for _ in range(player_count)]

    dealer_round_stats = {
        "profits": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": [],
        "fans": []
    }

    non_dealer_round_stats = {
        "profits": [],
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
            all_fans[i].append(result["fan"])
            all_wins[i].append(result["won"])
            all_deal_in_as_winner[i].append(result["deal_in_as_winner"])
            all_deal_in_as_loser[i].append(result["deal_in_as_loser"])
            all_missed_hu[i].append(result["missed_hu"])

            target_stats = dealer_round_stats if i == dealer_index else non_dealer_round_stats
            target_stats["profits"].append(result["profit"])
            target_stats["wins"].append(result["won"])
            target_stats["deal_in_as_winner"].append(result["deal_in_as_winner"])
            target_stats["deal_in_as_loser"].append(result["deal_in_as_loser"])
            target_stats["missed_hu"].append(result["missed_hu"])
            target_stats["fans"].append(result["fan"])

        if not round_meta["dealer_continues"]:
            dealer_index = (dealer_index + 1) % player_count

    def_stats = {
        "profits": [],
        "fans": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": []
    }

    agg_stats = {
        "profits": [],
        "fans": [],
        "wins": [],
        "deal_in_as_winner": [],
        "deal_in_as_loser": [],
        "missed_hu": []
    }

    per_player_stats = []

    for i, player in enumerate(players):
        profit_sum = np.sum(all_profits[i])
        wins = all_wins[i]
        fans = [f for f in all_fans[i] if f > 0]

        stats = {
            "profit": profit_sum,
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
            def_stats["fans"].extend(fans)
            def_stats["wins"].append(stats["win_rate"])
            def_stats["deal_in_as_winner"].append(stats["deal_in_rate"])
            def_stats["deal_in_as_loser"].append(stats["deal_in_loss_rate"])
            def_stats["missed_hu"].append(stats["missed_win_rate"])
        elif player.get("strategy_type") == "AGG":
            agg_stats["profits"].append(stats["profit"])
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


def simulate_table(composition, cfg):
    """
    Simulate a full table trial with given composition using REAL Monte Carlo.
    Uses TempoDefender for defensive players and ValueChaser for aggressive players.
    """
    num_def = composition
    num_agg = 4 - composition

    players = []
    t_fan_threshold = cfg["t_fan_threshold"]
    
    # Get strategy thresholds and weights from config
    strategy_cfg = cfg.get("strategy_thresholds", {})
    weights_cfg = cfg.get("scoring_weights", {})
    
    tempo_thresholds = strategy_cfg.get("tempo_defender", {})
    value_thresholds = strategy_cfg.get("value_chaser", {})

    # Use TempoDefender strategy class for defensive players
    for _ in range(num_def):
        players.append({
            "strategy": TempoDefender(thresholds=tempo_thresholds, weights=weights_cfg),
            "strategy_type": "DEF"
        })
    # Use ValueChaser strategy class for aggressive players
    for _ in range(num_agg):
        players.append({
            "strategy": ValueChaser(target_threshold=t_fan_threshold, 
                                   thresholds=value_thresholds, 
                                   weights=weights_cfg),
            "strategy_type": "AGG"
        })

    result = _run_table(players, cfg, cfg["rounds_per_trial"])
    result["composition"] = composition
    return result


def simulate_custom_table(players, cfg, rounds_per_trial=None):
    """
    Run a table simulation with a custom list of players using REAL Monte Carlo.
    
    Args:
        players: List of player dicts with "strategy" and "strategy_type"
        cfg: Configuration dictionary
        rounds_per_trial: Number of rounds (defaults to cfg["rounds_per_trial"])
    
    Returns:
        Dictionary with aggregated statistics
    """
    if rounds_per_trial is None:
        rounds_per_trial = cfg.get("rounds_per_trial")
        if rounds_per_trial is None:
            raise ValueError("rounds_per_trial must be specified in config")
    result = _run_table(players, cfg, rounds_per_trial)
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
        all_agg_profits = []
        all_def_win_rates = []
        all_agg_win_rates = []
        all_def_deal_in_rates = []
        all_agg_deal_in_rates = []
        all_def_missed_hu_rates = []
        all_agg_missed_hu_rates = []
        all_def_fans = []
        all_agg_fans = []
        all_dealer_profits = []
        all_dealer_wins = []
        all_dealer_deal_in_rates = []
        all_dealer_deal_in_loss_rates = []
        all_dealer_missed_hu = []
        all_dealer_fans = []
        all_non_dealer_profits = []
        all_non_dealer_wins = []
        all_non_dealer_deal_in_rates = []
        all_non_dealer_deal_in_loss_rates = []
        all_non_dealer_missed_hu = []
        all_non_dealer_fans = []
        
        for _ in range(num_trials):
            trial_result = simulate_table(composition, cfg)
            
            if len(trial_result["defensive"]["profits"]) > 0:
                all_def_profits.extend(trial_result["defensive"]["profits"])
                all_def_win_rates.extend(trial_result["defensive"]["wins"])
                all_def_deal_in_rates.extend(trial_result["defensive"]["deal_in_as_winner"])
                all_def_missed_hu_rates.extend(trial_result["defensive"]["missed_hu"])
                all_def_fans.extend(trial_result["defensive"]["fans"])
            
            if len(trial_result["aggressive"]["profits"]) > 0:
                all_agg_profits.extend(trial_result["aggressive"]["profits"])
                all_agg_win_rates.extend(trial_result["aggressive"]["wins"])
                all_agg_deal_in_rates.extend(trial_result["aggressive"]["deal_in_as_winner"])
                all_agg_missed_hu_rates.extend(trial_result["aggressive"]["missed_hu"])
                all_agg_fans.extend(trial_result["aggressive"]["fans"])
            
            dealer_stats = trial_result["dealer"]
            non_dealer_stats = trial_result["non_dealer"]
            
            all_dealer_profits.extend(dealer_stats["profits"])
            all_dealer_wins.extend(dealer_stats["wins"])
            all_dealer_deal_in_rates.extend(dealer_stats["deal_in_as_winner"])
            all_dealer_deal_in_loss_rates.extend(dealer_stats["deal_in_as_loser"])
            all_dealer_missed_hu.extend(dealer_stats["missed_hu"])
            all_dealer_fans.extend(dealer_stats["fans"])
            
            all_non_dealer_profits.extend(non_dealer_stats["profits"])
            all_non_dealer_wins.extend(non_dealer_stats["wins"])
            all_non_dealer_deal_in_rates.extend(non_dealer_stats["deal_in_as_winner"])
            all_non_dealer_deal_in_loss_rates.extend(non_dealer_stats["deal_in_as_loser"])
            all_non_dealer_missed_hu.extend(non_dealer_stats["missed_hu"])
            all_non_dealer_fans.extend(non_dealer_stats["fans"])
        
        results[composition] = {
            "defensive": {
                "mean_profit": np.mean(all_def_profits) if len(all_def_profits) > 0 else 0.0,
                "std_profit": np.std(all_def_profits) if len(all_def_profits) > 0 else 0.0,
                "win_rate": np.mean(all_def_win_rates) if len(all_def_win_rates) > 0 else 0.0,
                "deal_in_rate": np.mean(all_def_deal_in_rates) if len(all_def_deal_in_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_def_missed_hu_rates) if len(all_def_missed_hu_rates) > 0 else 0.0,
                "mean_fan": np.mean(all_def_fans) if len(all_def_fans) > 0 else 0.0,
                "fan_distribution": all_def_fans
            },
            "aggressive": {
                "mean_profit": np.mean(all_agg_profits) if len(all_agg_profits) > 0 else 0.0,
                "std_profit": np.std(all_agg_profits) if len(all_agg_profits) > 0 else 0.0,
                "win_rate": np.mean(all_agg_win_rates) if len(all_agg_win_rates) > 0 else 0.0,
                "deal_in_rate": np.mean(all_agg_deal_in_rates) if len(all_agg_deal_in_rates) > 0 else 0.0,
                "missed_hu_rate": np.mean(all_agg_missed_hu_rates) if len(all_agg_missed_hu_rates) > 0 else 0.0,
                "mean_fan": np.mean(all_agg_fans) if len(all_agg_fans) > 0 else 0.0,
                "fan_distribution": all_agg_fans
            },
            "dealer": {
                "mean_profit": np.mean(all_dealer_profits) if len(all_dealer_profits) > 0 else 0.0,
                "std_profit": np.std(all_dealer_profits) if len(all_dealer_profits) > 0 else 0.0,
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
        {"strategy": NeutralPolicy(seed=None), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=None), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=None), "strategy_type": "NEU"}
    ]
    
    # Simulate one round using 4-player table simulation
    dealer_index = 0 if is_dealer else 1
    round_results, _ = simulate_table_round(players, cfg, dealer_index)
    
    # Return only the test player's (first player's) results
    return round_results[0]


def run_simulation(strategy_fn: Union[Callable[[Union[int, float]], bool], BaseStrategy], 
                  cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a single trial (multiple rounds) with 1 test player + 3 neutral players.
    
    This is a convenience wrapper that uses simulate_custom_table() internally.
    All Mahjong games are 4-player; this just simplifies the interface.
    
    Args:
        strategy_fn: Strategy function or strategy object (BaseStrategy instance)
        cfg: Configuration dictionary
    
    Returns:
        Dictionary with aggregated statistics for this trial
    """
    from .players import NeutralPolicy
    
    # Determine strategy type for test player
    fan_min = cfg.get("fan_min", 1)
    fan_threshold = cfg.get("t_fan_threshold", 3)
    test_strategy_type = "DEF"  # Default
    
    # Get neutral policy thresholds from config
    strategy_cfg = cfg.get("strategy_thresholds", {})
    neutral_thresholds = strategy_cfg.get("neutral_policy", {})
    
    # Support both strategy objects and functions
    if isinstance(strategy_fn, BaseStrategy):
        # Strategy object: determine type from class name
        if isinstance(strategy_fn, TempoDefender):
            test_strategy_type = "DEF"
        elif isinstance(strategy_fn, ValueChaser):
            test_strategy_type = "AGG"
        else:
            # Default based on should_hu behavior
            if strategy_fn.should_hu(fan_min, 0.0, None, fan_min, fan_threshold):
                test_strategy_type = "DEF"
            else:
                test_strategy_type = "AGG"
    elif callable(strategy_fn):
        # Legacy function-based strategy
        if strategy_fn(fan_min):
            test_strategy_type = "DEF"
        elif not strategy_fn(fan_threshold - 1):
            test_strategy_type = "AGG"
    
    # Create 4-player table: 1 test player + 3 neutral players
    players = [
        {"strategy": strategy_fn, "strategy_type": test_strategy_type},
        {"strategy": NeutralPolicy(seed=None, thresholds=neutral_thresholds), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=None, thresholds=neutral_thresholds), "strategy_type": "NEU"},
        {"strategy": NeutralPolicy(seed=None, thresholds=neutral_thresholds), "strategy_type": "NEU"}
    ]
    
    # Use 4-player table simulation
    table_result = simulate_custom_table(players, cfg)
    
    # Extract test player's (first player's) statistics
    test_player_stats = table_result["per_player"][0]
    
    return {
        "profit": test_player_stats["profit"],
        "mean_fan": test_player_stats["mean_fan"],
        "win_rate": test_player_stats["win_rate"],
        "deal_in_rate": test_player_stats["deal_in_rate"],
        "deal_in_loss_rate": test_player_stats["deal_in_loss_rate"],
        "missed_win_rate": test_player_stats["missed_win_rate"],
        "fan_distribution": test_player_stats["fan_distribution"]
    }


def run_multiple_trials(strategy_fn: Union[Callable[[Union[int, float]], bool], BaseStrategy], 
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
    all_mean_fans = []
    all_win_rates = []
    all_deal_in_rates = []
    all_deal_in_loss_rates = []
    all_missed_win_rates = []
    all_fan_distributions = []
    
    for _ in range(num_trials):
        result = run_simulation(strategy_fn, cfg)
        all_profits.append(result["profit"])
        all_mean_fans.append(result["mean_fan"])
        all_win_rates.append(result["win_rate"])
        all_deal_in_rates.append(result["deal_in_rate"])
        all_deal_in_loss_rates.append(result["deal_in_loss_rate"])
        all_missed_win_rates.append(result["missed_win_rate"])
        all_fan_distributions.extend(result["fan_distribution"])
    
    return {
        "profits": np.array(all_profits),
        "mean_fans": np.array(all_mean_fans),
        "win_rates": np.array(all_win_rates),
        "deal_in_rates": np.array(all_deal_in_rates),
        "deal_in_loss_rates": np.array(all_deal_in_loss_rates),
        "missed_win_rates": np.array(all_missed_win_rates),
        "fan_distribution": np.array(all_fan_distributions),
        "num_trials": num_trials
    }

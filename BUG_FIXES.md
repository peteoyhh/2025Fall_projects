# Bug Fixes Summary

## Issues Found and Fixed

### 1. **Tile Removal Logic in `_evaluate_post_discard_hand`**
**Problem:** 
- Original code used list comprehension `[t for t in hand.tiles if t != tile_to_discard]`
- This removes ALL instances of the tile, but we only want to remove ONE instance
- If a tile appears multiple times, we should only remove one copy

**Fix:**
- Changed to use `hand.tiles.copy()` and `temp_tiles.remove(tile_to_discard)`
- This correctly removes only one instance
- Added try-except to handle edge case where tile is not in hand

**Location:** `mahjong_sim/strategies.py`, line 253-260

---

### 2. **Wall Remaining Calculation in `_get_dynamic_weights`**
**Problem:**
- Original code estimated wall starts at 84 tiles
- Actual calculation: 136 total - 53 dealt = 83 remaining
- Incorrect estimate could affect dynamic weight calculations

**Fix:**
- Updated to use correct value: 83 tiles remaining after dealing
- Updated normalization formula: `(83 - wall_remaining) / 83.0`

**Location:** `mahjong_sim/strategies.py`, line 340-346

---

### 3. **Hand Completion Normalization**
**Problem:**
- Original code: `min(hand_completion / 15.0, 1.0)`
- Could produce negative values if hand_completion < 0
- Negative completion scores are possible (many isolated tiles)

**Fix:**
- Added bounds checking: `min(max(hand_completion / 15.0, 0.0), 1.0)`
- Ensures normalized value is always between 0.0 and 1.0

**Location:** `mahjong_sim/strategies.py`, line 358

---

### 4. **Game Progress Calculation Enhancement**
**Problem:**
- Original code only used turn number for progress calculation
- Turn number alone may not accurately reflect game state
- Wall remaining is a better indicator of game progress

**Fix:**
- Combined wall remaining (70% weight) and turn number (30% weight)
- More accurately reflects actual game progress
- Handles edge cases (wall exhausted = late game)

**Location:** `mahjong_sim/strategies.py`, line 340-354

---

## Testing

All fixes have been tested:
- ✅ Import tests pass
- ✅ Dynamic weights calculation works correctly
- ✅ No linter errors
- ✅ Edge cases handled (empty hands, negative scores, etc.)

---

## Impact

These fixes ensure:
1. **Correct tile removal** when evaluating post-discard hand quality
2. **Accurate game progress** calculation for dynamic weight adjustments
3. **Robust handling** of edge cases (negative scores, empty hands, etc.)
4. **Better strategy decisions** based on accurate game state assessment


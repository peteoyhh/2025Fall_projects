# Strategy Enhancement Summary

## Overview
This document describes the significant enhancements made to the Mahjong strategy system to incorporate human-like per-turn decision-making, addressing the requirement that strategies differ in more than just when Hu is declared.

---

## 1. Enhanced TableState

### Changes
- Added `opponent_discards_by_suit`: Dictionary mapping suit -> list of tiles discarded by opponents
- Added `total_tiles_discarded`: Total count of discarded tiles for analysis

### Purpose
Enables strategies to analyze opponent discard patterns and make informed decisions about suit availability and safety.

---

## 2. Hand Completion Metric

### New Function: `_hand_completion_score()`
Estimates how close a hand is to a valid winning structure using heuristics:

**Components:**
- **Completed melds**: Already formed melds (Pong/Chi/Gong) - weight: 3.0
- **Pairs**: Tiles that can form eyes - weight: 1.5
- **Tatsu**: 2-tile sequences that can become chi - weight: 0.8
- **Isolated tiles**: Tiles with no nearby tiles (penalty) - weight: -0.5

**Usage:**
- Strategies use this score to adjust their aggressiveness
- Higher completion = more conservative play
- Lower completion = more exploratory play

---

## 3. Dynamic Strategy Weighting

### New Function: `_get_dynamic_weights()`
Adjusts strategy weights based on:
- **Hand completion level**: Higher completion → more safety-focused
- **Round progression**: Early game → exploration, Late game → safety

**Dynamic Adjustments:**
- Safety weight: 0.3 (early) → 1.0 (late)
- Potential weights: 1.0 (low completion) → 0.7 (high completion)

**Impact:**
- Strategies adapt their behavior as the game progresses
- Early rounds tolerate more risk for exploration
- Late rounds prioritize safety and completion

---

## 4. Opponent Discard Pattern Awareness

### New Function: `_opponent_suit_availability()`
Analyzes opponent discard patterns to estimate suit availability:

**Logic:**
- Suits frequently discarded by opponents → more available/safer
- Suits rarely discarded → less available (higher risk)

**Usage:**
- Strategies adjust their suit preferences based on availability
- ValueChaser strongly prefers available suits
- TempoDefender considers availability but prioritizes safety

---

## 5. Post-Discard Hand Quality Evaluation

### New Function: `_evaluate_post_discard_hand()`
Evaluates hand quality after discarding a specific tile:

**Components:**
- **Isolated tile reduction**: Prefer discards that reduce isolated tiles (weight: 2.0)
- **Structure clarity**: Prefer discards that improve pairs/tatsu count (weight: 1.5)

**Impact:**
- Strategies now consider the resulting hand structure, not just current tile value
- Prefers discards that improve hand organization
- Reduces isolated tiles that are hard to use

---

## 6. Enhanced Strategy Implementations

### TempoDefender (Defensive Strategy)

**Enhanced `choose_discard()`:**
1. Calculates hand completion score
2. Gets dynamic weights based on completion and turn progression
3. Analyzes opponent suit availability
4. Evaluates post-discard hand quality for each tile
5. Combines factors: **safety > post-discard quality > potential**

**Key Differences:**
- Prioritizes safety over all other factors
- Uses dynamic weights that increase safety focus in late game
- Considers opponent patterns but doesn't strongly favor available suits

### ValueChaser (Aggressive Strategy)

**Enhanced `choose_discard()`:**
1. Calculates hand completion score
2. Gets dynamic weights based on completion and turn progression
3. Analyzes opponent suit availability
4. Evaluates post-discard hand quality for each tile
5. Combines factors: **dominant suit > suit availability > potential > post-discard quality**

**Key Differences:**
- Strongly prioritizes dominant suit retention
- Actively seeks suits that opponents are discarding (more available)
- Less safety-focused, more risk-tolerant
- Dynamic weights adjust exploration vs. completion focus

---

## 7. Configuration Updates

### New Parameters in `configs/base.yaml`:

```yaml
# Hand completion evaluation weights
hand_completion_weights:
  completed_meld: 3.0
  pair: 1.5
  tatsu: 0.8
  isolated_penalty: -0.5

# Post-discard evaluation weights
post_discard_weights:
  isolated_reduction: 2.0
  structure_clarity: 1.5
  completion_improvement: 1.0
```

---

## 8. Code Updates

### Files Modified:

1. **`mahjong_sim/strategies.py`**
   - Enhanced `TableState` dataclass
   - Added `_hand_completion_score()` function
   - Added `_opponent_suit_availability()` function
   - Added `_evaluate_post_discard_hand()` function
   - Added `_get_dynamic_weights()` function
   - Completely rewrote `TempoDefender.choose_discard()`
   - Completely rewrote `ValueChaser.choose_discard()`

2. **`mahjong_sim/real_mc.py`**
   - Added `opponent_discards_by_player` tracking in `initialize_round()`
   - Updated all `TableState` creations to include opponent discard information
   - Tracks each player's discards for opponent analysis

3. **`configs/base.yaml`**
   - Added `hand_completion_weights` section
   - Added `post_discard_weights` section

4. **`experiments/run_experiment_1.py`**
   - Updated to merge new weight configurations

5. **`main.py`**
   - Updated to merge new weight configurations

---

## 9. Strategy Differences Summary

### Per-Turn Decision Differences:

| Aspect | TempoDefender | ValueChaser |
|--------|---------------|-------------|
| **Safety Priority** | Very High | Low |
| **Suit Preference** | Neutral | Strongly favors dominant suit |
| **Opponent Pattern Use** | Moderate | Strong (seeks available suits) |
| **Post-Discard Evaluation** | High weight | Moderate weight |
| **Dynamic Adjustment** | Increases safety in late game | Increases exploration in early game |
| **Hand Completion Impact** | More conservative when close | More aggressive when far |

### Key Behavioral Differences:

1. **Early Game:**
   - TempoDefender: Moderate exploration, safety-focused
   - ValueChaser: High exploration, seeks dominant suit

2. **Mid Game:**
   - TempoDefender: Increasing safety focus
   - ValueChaser: Building toward high-fan combinations

3. **Late Game:**
   - TempoDefender: Maximum safety, quick completion
   - ValueChaser: Still pursues high-fan, but considers bailout

4. **Discard Selection:**
   - TempoDefender: Safest tiles with lowest potential
   - ValueChaser: Non-dominant suit tiles, low potential, but considers availability

---

## 10. Testing Recommendations

1. **Run Experiment 1** to verify strategies still produce meaningful comparisons
2. **Check discard patterns** in logs to verify different decision-making
3. **Monitor hand completion scores** to verify dynamic adjustments
4. **Verify opponent pattern tracking** works correctly

---

## 11. Backward Compatibility

- All existing interfaces maintained
- Legacy strategy functions (`defensive_strategy`, `aggressive_strategy`) still available
- Configuration file additions are optional (defaults provided)
- Existing experiments should work without modification

---

## Summary

The strategies now make **significantly different decisions every turn** based on:
- Hand completion assessment
- Dynamic weight adjustments
- Opponent discard pattern analysis
- Post-discard hand quality evaluation

This creates realistic, human-like decision-making that goes far beyond simple Hu declaration thresholds.


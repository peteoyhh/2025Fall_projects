# Code Changes Summary

## 1. Unified Scoring Formula

**File:** `mahjong_sim/strategies.py` - `TempoDefender.choose_discard()`

Converted from `discard_score` (lower is better) to `keep_score` (higher is better) to match ValueChaser.

```python
# Before: discard_score = -safety_weighted * 1.5 + ...
# After:  keep_score = safety_weighted * 1.5 + ...
```

---

## 2. Bug Fixes

**File:** `mahjong_sim/strategies.py`

- **Pairs counting:** Changed `count >= 2` → `count == 2` (exclude triplets)
- **Tatsu counting:** Changed `<= 2` → `<= 1` (only consecutive or one-gap)
- **Boundary check:** Added `max(1, ...)` to prevent `fan=0` wins in `TempoDefender.should_hu()`

---

## 3. ValueChaser Adjustments

**File:** `mahjong_sim/strategies.py`

- `bailout_risk_threshold`: 0.65 → 0.8
- Added medium-risk condition: `risk > 0.5 and fan >= 2 and threshold <= 3`

---

## 4. TempoDefender Enhancement

**File:** `mahjong_sim/strategies.py`

Added medium-risk win condition: `risk >= 0.3 and fan >= fan_min`

---

## 5. NeutralPolicy Redesign

**File:** `mahjong_sim/players.py`

Redesigned with three-tier risk strategy (ValueChaser-like):

- **Low risk** (`risk < 0.45`): `fan >= 3`
- **Medium risk** (`0.45 ≤ risk < 0.70`): `fan >= 2`
- **High risk** (`risk ≥ 0.70`): `fan >= 1`

**Config:** `target_fan: 3`, `medium_risk_threshold: 0.45`, `bailout_risk_threshold: 0.70`

---

## 6. Strategy Risk Thresholds

**Files:** `mahjong_sim/strategies.py`, `mahjong_sim/players.py`, `configs/base.yaml`

| Strategy | Low Risk | Medium Risk | High Risk |
|----------|----------|-------------|-----------|
| **DEF** | `< 0.35` → `fan >= 2` | `0.35-0.60` → `fan >= 1` | `≥ 0.60` → `fan >= 1` |
| **NEU** | `< 0.45` → `fan >= 3` | `0.45-0.70` → `fan >= 2` | `≥ 0.70` → `fan >= 1` |
| **AGG** | `< 0.55` → `fan >= 5` | `0.55-0.80` → `fan >= 3` | `≥ 0.80` → `fan >= 1` |

**Config changes:**
- `t_fan_threshold`: 3 → 5
- `tempo_defender`: Added `medium_risk_threshold: 0.35`, `high_risk_threshold: 0.60`
- `value_chaser`: Added `medium_risk_threshold: 0.55`, `bailout_risk_threshold: 0.80`

---

## 7. Experiment 1: 1v3 → 2v2

**File:** `experiments/run_experiment_1.py`

Changed from 1 test player + 3 neutral players to 2 test players + 2 neutral players.

- `build_players()`: Creates 2 test players + 2 NEU players
- `summarize_trials()`: Aggregates stats from both test players (positions 0 and 1)

---

## 8. Other Changes

- **Plotting:** Changed "Total" → "Total Wins" in fan distribution plots
- **Experiment 2:** Added profit comparison bar chart
- **Random seeds:** Removed all fixed seeds, use `seed=None` everywhere
- **Tests:** Updated to match new thresholds and behaviors

---

*Last Updated: December 2025*

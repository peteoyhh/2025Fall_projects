# Monte Carlo Simulation of Strategic Trade-offs in Beijing Mahjong

**Authors:** Xu(Pete) Chen, Bohan Shan  
**NetIDs:** xc74, bohans3  

---

## 🀄 Introduction

Mahjong is a traditional four-player strategy game that blends elements of probability, pattern recognition, and risk–reward decision-making.  
This project focuses on **Beijing-style Mahjong**, a ruleset widely played in northern China.  

Each player begins with **13 tiles** and draws one on each turn, discarding one until achieving a valid **14-tile winning hand (Hu)**.  
A standard winning hand must consist of **four melds (sets)** and **one pair (eyes)**, where melds can be:
![Beijing Mahjong Example Board](images/mahjong_board.png)
- **Pongs** – three identical tiles (e.g., three 5 of Characters)  
- **Chis** – three consecutive tiles of the same suit (e.g., 3–4–5 of Dots)  
- **Gongs** – four identical tiles (a special type of Pung that yields a bonus fan)  
- The **pair (eyes)** is any two identical tiles (e.g., two Red Dragons)

Unlike southern variants such as Sichuan Mahjong that emphasize continuous rounds or “blood battle” mechanics, the **Beijing style** uses a **fan-based scoring system** with independent hands and exponential payoffs determined by the complexity of the winning pattern.

The total score for a winning hand typically follows an exponential relationship:
`Score = B × 2^fan`
where `B` is a fixed base point (e.g., 2 or 4).

---

## 🚀 Getting Started

### Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuration

All simulation parameters are configured in `configs/base.yaml`:

#### Basic Game Parameters

```yaml
base_points: 10              # Base point value for scoring (B in Score = B * 2^fan)
fan_min: 1                  # Minimum fan for defensive strategy (Pi Hu = 1 fan)
t_fan_threshold: 3          # Fan threshold for aggressive strategy
penalty_deal_in: 1          # Deal-in penalty multiplier
rounds_per_trial: 20        # Number of rounds per trial
trials: 50                  # Number of trials to run (more trials provide more stable results but take longer)
```

#### Strategy Thresholds

These parameters control when strategies decide to claim actions (Hu, Gong, Pong, Chi):

```yaml
strategy_thresholds:
  tempo_defender:
    high_risk_threshold: 0.5        # Risk level at which to accept wins even below fan_min
    gong_risk_threshold: 0.35       # Maximum risk to claim Gong
    pong_risk_threshold: 0.5        # Maximum risk to claim Pong
    chi_risk_threshold: 0.35        # Maximum risk to claim Chi
    risk_fan_adjustment: 0.5        # Fan adjustment when accepting high-risk wins
    
  value_chaser:
    bailout_risk_threshold: 0.65    # Risk level to bail out and accept fan_min wins
    chi_risk_threshold: 0.7         # Maximum risk to claim Chi
    chi_wall_threshold: 25          # Minimum wall tiles remaining to claim Chi
    
  neutral_policy:
    risk_threshold: 0.4             # Risk level to accept wins
    continue_probability: 0.2       # Probability to continue when risk is low
```

#### Tile Evaluation Heuristics

These weights control how tiles are evaluated for discard decisions:

```yaml
scoring_weights:
  pair_potential: 3          # Weight for tiles that can form pairs/pongs
  sequence_potential: 0.5    # Weight for tiles that can form sequences (chi)
  honor_value: 0.8           # Base value for honor tiles (Feng/Jian)
  suit_penalty: 2            # Penalty for tiles not matching dominant suit (ValueChaser)
  safety_weight: 0.3         # Weight for safety (tiles already seen in discard pile)
```

#### Hand Completion Evaluation

These weights assess how close a hand is to completion:

```yaml
hand_completion_weights:
  completed_meld: 3.0        # Score for each completed meld (Pong/Chi/Gong)
  pair: 1.5                  # Score for each pair (potential eyes)
  tatsu: 0.8                 # Score for each tatsu (2-tile sequence that can become chi)
  isolated_penalty: -0.5     # Penalty for each isolated tile (no nearby tiles)
```

#### Post-Discard Evaluation

These weights evaluate hand quality after discarding a tile:

```yaml
post_discard_weights:
  isolated_reduction: 2.0    # Bonus for reducing isolated tiles
  structure_clarity: 1.5     # Bonus for improving pairs/tatsu count
  completion_improvement: 1.0 # Bonus for improving overall completion
```

#### Risk Calculation

```yaml
risk_calculation:
  max_denominator: 100       # Denominator for risk calculation (risk = discards / max(denominator, wall + discards))
```

#### Experiment Parameters

```yaml
experiment:
  num_compositions: 5       # Number of table compositions to test
  theta_values: [0, 1, 2, 3, 4]  # Values of theta (number of defensive opponents)
  regression_samples: 100   # Number of samples for regression analysis
```

### Running Experiments

**Run a specific experiment:**
```bash
python main.py --experiment 1    # Strategy comparison
python main.py --experiment 2    # Table composition analysis
```

**Run all experiments (runs experiments 1 and 2):**
```bash
python main.py --all
```

### Running Tests

**Run all tests with coverage:**
```bash
pytest pytest/ --cov=mahjong_sim --cov-report=term-missing --cov-report=html
```

**Run tests without coverage:**
```bash
pytest pytest/ -v
```

**View coverage report:**
```bash
open htmlcov/index.html
```


---

## 📁 Project Structure

```
597PRFINAL/
├── configs/
│   └── base.yaml              # Configuration file for all experiments
├── experiments/
│   ├── run_experiment_1.py   # Strategy comparison experiment
│   └── run_experiment_2_table.py  # Table composition analysis
├── mahjong_sim/
│   ├── __init__.py
│   ├── real_mc.py            # Core Monte Carlo simulation engine
│   ├── scoring.py            # Scoring functions (score, profit, cost)
│   ├── strategies.py         # Strategy classes (TempoDefender, ValueChaser) and interfaces
│   ├── players.py            # Player classes and NeutralPolicy
│   ├── utils.py              # Statistical utilities and comparisons
│   └── plotting.py           # Visualization functions
├── pytest/                    # Test suite
│   ├── test_simulation.py     # Basic simulation tests
│   ├── test_simulation_extended.py  # Extended simulation tests
│   ├── test_strategies.py    # Strategy function tests
│   ├── test_scoring.py       # Scoring function tests
│   ├── test_players.py       # Player and NeutralPolicy tests
│   ├── test_table.py         # Table simulation tests
│   └── test_utils.py          # Utility and statistics tests
├── output/                    # Experiment output files
├── plots/                     # Generated plots and visualizations
├── main.py                    # Main entry point for running experiments
├── pytest.ini                 # Pytest configuration
└── requirements.txt           # Python dependencies
```

---

### Common Fan Sources in Beijing Rules

| **Category** | **Example** | **Fan Value** |
|---------------|-------------|----------------|
| **Basic hand** | Self-draw, Concealed hand, All simples | 1 fan |
| **Common wins** | All pongs, Mixed triple chow | 2 fan |
| **Advanced hands** | Pure flush, Little dragons | 4–6 fan |
| **Add-on bonuses** | Gong +1 fan; "Gong open" win +1 fan | Variable (1–2 fan) |

#### 1. Basic Hand — 1 Fan Each
**① Self-draw — 1 fan**  
Definition: You win by drawing the winning tile yourself.  
Requirements:  
- Winning tile must come from your own draw  
- Melds (chi/pong) do not affect this bonus
    
**② Concealed hand — 1 fan**  
Definition: You win with a completely closed hand.  
Requirements:  
- No exposed melds  
- Win may be self-draw or discard depending on rule set
  
**③ All simples — 1 fan**  
Definition: Hand contains no terminals (1 or 9) and no honours(Winds + Dragons).  
Requirements:  
- Tiles must be 2–8 only  
- Melds allowed as long as tiles meet criteria  
#### 2. Common Wins — 2 Fan Each
**④ All pongs — 2 fan**  
Definition: Hand consists of four pong/gong sets and one pair.  
Requirements:  
- Exposed or concealed allowed  
- Pair may be any tile
  
**⑤ Mixed triple chow — 2 fan**  
Definition: Same numbered chi appears in all three suits.  
Example: 4–5–6 in characters(wans), dots(tongs), and bamboos(sous)  
Requirements:  
- Three identical sequences, one in each suit  
#### 3. Advanced Hands — 4–6 Fan Each
**⑥ Pure flush — 4–6 fan**  
Definition: Whole hand uses tiles from one suit, no honours(Winds + Dragons).  
Fan range:  
- Exposed melds → lower (4 fan)  
- Fully concealed → higher (6 fan)
   
**⑦ Little dragons — 4–6 fan**  
Definition:  
- Two dragon pongs/gongs  
- Pair made from the remaining dragon  
Requirements:  
- Dragon melds may be exposed or concealed  
- Pair must be the third dragon  
#### 4. Add-on Bonuses — +1 to +2 Fan
**⑧ Gong — +1 fan**  
Definition: Gong formed by upgrading an existing Pong meld (from self-draw or discard).  
Bonus: +1 fan per gong  

**⑨ "Gong open" win — +1 fan**  
Definition: Win on the tile drawn immediately after making a gong.  
Bonus: +1 fan, added on top of gong bonuses  

---

### Pi Hu Rule and Strategy Implications

In our simulation, **Pi Hu with 1 fan is allowed** as the minimum valid winning hand.  
Traditional Beijing rules require at least one fan to declare a win, and our implementation enforces this:  
A structurally complete hand of four melds plus one pair **must have at least 1 fan to win** (0 fan is invalid).  
**Pi Hu (1 fan)** represents the most basic winning hand and is fully allowed.

This creates two key consequences for the simulation:
1. Defensive players can win with **1 fan (Pi Hu)** as soon as they reach this minimum threshold, reducing exposure to deal-in risk.  
2. Aggressive players pursue higher-fan outcomes (typically 3+ fan), choosing to continue drawing rather than accepting 1-fan Pi Hu wins.


---

## ⚙️ Methodology

This project uses a **Monte Carlo simulation** to model and compare long-term outcomes of player strategies under Beijing-style Mahjong rules.  
It does **not** involve any machine learning or predictive modeling; all results are based purely on random sampling and probabilistic reasoning.

---

### Phase 1 – Design

This project implements a **real Monte Carlo simulation** using actual tile-based gameplay mechanics.  
Each simulated round represents a complete hand among four players using a full **136-tile deck** (Wan, Tiao, Tong, Feng, Jian tiles).

**Game Mechanics:**
- **Deal:** Each player receives 13 tiles; dealer receives 14 tiles
- **Draw and Discard:** Players take turns drawing from the wall and discarding tiles
- **Player Actions:** Players can declare **Pong** (triplet from discard), **Gong** (quad, upgraded from Pung), or **Hu** (win)
- **Winning Detection:** Real pattern matching to detect valid winning hands (4 melds + 1 pair)
- **Fan Calculation:** Based on actual hand patterns (triplets, sequences, Gongs, special patterns)

**Scoring:**
Each round yields one or more winning events (self-draw or deal-in win).  
Scoring follows the Beijing Mahjong rule: `Score = B × 2^fan` where `B` is the base unit score and total fan includes bonuses from hand patterns and Gongs.  
Deal-in penalties are subtracted from the losing player's total; self-draws distribute points from all three opponents.  
The **minimum fan requirement** ensures that any hand with `Fan < 1` is invalid and yields no win. **Pi Hu with 1 fan is allowed** and represents the most basic winning hand.

---

### Phase 2 – Experiments

We define two player strategies that make differentiated decisions at each turn:

- **Defensive strategy (TempoDefender):** 
  - **Hu Declaration:** Declares Hu immediately when `fan >= fan_min` (typically 1) or when risk is high (`risk >= high_risk_threshold`); minimizes further risk
  - **Claim Decisions:** Rarely claims chi/pong/gong to avoid exposing melds (only when risk is below respective thresholds)
  - **Discard Logic:** 
    - Prioritizes safety: discards safest tiles (most seen in discard pile)
    - Considers hand completion: adjusts aggressiveness based on how close hand is to completion
    - Evaluates post-discard quality: prefers discards that reduce isolated tiles and improve structure
    - Uses dynamic weights: increases safety focus in late game (when wall is low)
    - Considers opponent patterns: moderately uses suit availability information
  
- **Aggressive strategy (ValueChaser):** 
  - **Hu Declaration:** Declares Hu only if `fan >= t_fan_threshold` (typically 3); falls back to minimum when risk exceeds `bailout_risk_threshold` (0.65)
  - **Claim Decisions:** Willing to claim pong/gong for fan bonuses; can claim chi early if wall has sufficient tiles (`wall_remaining > chi_wall_threshold`)
  - **Discard Logic:**
    - Strongly prioritizes dominant suit retention: heavy penalty for non-dominant suit tiles
    - Actively seeks available suits: prefers tiles from suits opponents are discarding (more available)
    - Considers hand completion: adjusts exploration vs. completion focus dynamically
    - Evaluates post-discard quality: considers structure improvement but prioritizes suit matching
    - Uses dynamic weights: more exploration in early game, more completion focus in late game
    - Less safety-focused: lower safety weight, more risk-tolerant

**Key Heuristic Components:**

Both strategies use the following evaluation functions:

1. **Hand Completion Score:** Estimates proximity to winning structure based on:
   - Completed melds (Pong/Chi/Gong already formed)
   - Pairs (potential eyes)
   - Tatsu (2-tile sequences that can become chi)
   - Isolated tiles (penalty for tiles with no nearby tiles)

2. **Dynamic Weight Adjustment:** Weights change based on:
   - Hand completion level (higher completion → more conservative)
   - Round progression (early game → exploration, late game → safety)
   - Wall remaining (primary indicator, 70% weight) + turn number (30% weight)

3. **Opponent Discard Pattern Analysis:** 
   - Tracks opponent discards by suit
   - Suits frequently discarded → more available/safer
   - Suits rarely discarded → less available (higher risk)

4. **Post-Discard Hand Quality Evaluation:**
   - Evaluates hand structure after discarding each tile
   - Prefers discards that reduce isolated tiles
   - Prefers discards that improve structure clarity (pairs/tatsu count)

Each simulation trial consists of **20 rounds** (configurable via `rounds_per_trial`) played among all 4 players, with multiple trials (default: 50) to obtain stable distributions.

| **Experiment** | **Variable Manipulated** | **Purpose** |
|-----------------|--------------------------|-------------|
| 1. Strategy comparison | Compare DEF vs AGG under identical conditions | Test H1 (profit difference) |
| 2. Table composition sweep | Vary proportion of DEF players, theta = 0, 1, 2, 3, 4 | Analyze strategy performance across different table compositions |

---

### Phase 3 – Analysis

Simulation outputs are aggregated across all trials to estimate:

- Expected profit per trial: E(Score)  
- Variance and confidence intervals  
- Win rate, self-draw rate, and deal-in rate  
- Fan distribution (frequency of 1–16 fan outcomes)  
- Risk metrics such as maximum drawdown and ruin probability under a finite bankroll  

Statistical comparisons between strategy types use **two-sample t-tests** and **confidence intervals**.  
For composition analysis, we run a **regression of profit against theta** (the proportion of defensive opponents) to analyze how table composition affects strategy performance.  

All experiments use **modular Python code** and configuration-driven runs via YAML inputs.


---

## 🎯 Hypotheses

**H1:**  
Defensive players, who prioritize winning whenever possible, will achieve higher expected long-term monetary profit than aggressive players, who only win on hands meeting or exceeding a specified fan threshold.
1. From our results, we found that after 50 trials, the average profit that the defensive players earned was higher than the aggressive players, which proved our hypothesis.
   ![profit comparison](plots/experiment_1/profit_comparison.png)
2. Our simulation results clearly indicate that the defensive strategy is more successful in achieving victory. We found that the win rate for defensive players was significantly higher than that of aggressive players. In this simulated environment, adopting a defensive approach (focusing on stability and minimizing risk) strongly correlated with a higher frequency of winning rounds. While defensive players won more often, the advantage largely disappeared when analyzing total earnings. Despite the considerable difference in win rate, the difference in total profit between the two player types was marginal. This suggests that while aggressive players win less frequently, they have a higher probability of achieving high-scoring, high-Fan hands when they do win. This is likely due to their willingness to pursue complex, riskier hand combinations that yield significant profit spikes in single games.
   ![win_rate comparison](plots/experiment_1/win_rate_comparison.png)
3. The Fan distribution reveals a key distinction: at Fan value = 3, aggressive players exhibit a significantly higher win count. This outcome is likely driven by our simulation's design, as aggressive players are programmed to declare a win once they achieve the Fan_threshold of 3 or higher. Surprisingly, at the high end, specifically Fan value = 5, defensive players recorded five wins. We hypothesize that this result occurred because defensive players, when dealt exceptionally strong starting hands, capitalize on the high-Fan opportunities, leading them to outperform aggressive players at that specific upper limit.
   ![fan distribution](plots/experiment_1/fan_distribution.png)

---

## 🀄️ Conclusion

1. Defensive players have a higher win rate and earn more - Even though aggressive players achieve higher fan values, their much lower win frequency prevents those large hands from earning.
2. Aggressive players do not gain an advantage even when surrounded by other aggressive players - The aggressive strategy's structural weaknesses—low win rate, high missed-Hu rate, and dependency on large hands—outweigh any potential synergy or table-composition advantage.

---


## 🧪 Testing

**Test files:**
- `test_simulation.py`: Basic simulation functionality
- `test_simulation_extended.py`: Extended simulation tests
- `test_strategies.py`: Strategy function tests
- `test_scoring.py`: Scoring function tests
- `test_players.py`: Player and NeutralPolicy tests
- `test_table.py`: Table simulation tests
- `test_utils.py`: Statistical utility tests

---

## 📚 Reference

Chen, J. C., Tang, S. C., & Wu, I. C. (n.d.). *Monte-Carlo simulation for Mahjong.*  
National Yang Ming Chiao Tung University Academic Hub.  
[https://scholar.nycu.edu.tw/en/publications/monte-carlo-simulation-for-mahjong](https://scholar.nycu.edu.tw/en/publications/monte-carlo-simulation-for-mahjong)

*Image from:*  
Chen, J. C., Tang, S. C., & Wu, I. C. (n.d.). *Monte-Carlo simulation for Mahjong.*  
National Yang Ming Chiao Tung University Academic Hub.  
[https://scholar.nycu.edu.tw/en/publications/monte-carlo-simulation-for-mahjong](https://scholar.nycu.edu.tw/en/publications/monte-carlo-simulation-for-mahjong)

---

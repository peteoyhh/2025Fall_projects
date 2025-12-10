# Monte Carlo Simulation of Strategic Trade-offs in Beijing Mahjong

**Authors:** Xu Chen, BoHan Shan  
**NetIDs:** xc74, bohans3  

---

## 🀄 Introduction

Mahjong is a traditional four-player strategy game that blends elements of probability, pattern recognition, and risk–reward decision-making.  
This project focuses on **Beijing-style Mahjong**, a ruleset widely played in northern China.  

Each player begins with **13 tiles** and draws one on each turn, discarding one until achieving a valid **14-tile winning hand (Hu)**.  
A standard winning hand must consist of **four melds (sets)** and **one pair (eyes)**, where melds can be:
![Beijing Mahjong Example Board](images/mahjong_board.png)
- **Pungs** – three identical tiles (e.g., three 5 of Characters)  
- **Chows** – three consecutive tiles of the same suit (e.g., 3–4–5 of Dots)  
- **Kongs** – four identical tiles (a special type of Pung that yields a bonus fan)  
- The **pair (eyes)** is any two identical tiles (e.g., two Red Dragons)

Unlike southern variants such as Sichuan Mahjong that emphasize continuous rounds or “blood battle” mechanics, the **Beijing style** uses a **fan-based scoring system** with independent hands and exponential payoffs determined by the complexity of the winning pattern.

The total score for a winning hand typically follows an exponential relationship:
where `B` is a fixed base point (e.g., 2 or 4).

---

### Common Fan Sources in Beijing Rules

| **Category** | **Example** | **Fan Value** |
|---------------|-------------|----------------|
| **Basic hand** | Self-draw, Concealed hand, All simples | 1 fan |
| **Common wins** | All pungs, Mixed triple chow | 2 fan |
| **Advanced hands** | Pure flush, Little dragons | 4–6 fan |
| **Add-on bonuses** | Kong +1 fan; "Kong open" win +1 fan | Variable (1–2 fan) |

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
Definition: Hand contains no terminals (1 or 9) and no honors.  
Requirements:  
- Tiles must be 2–8 only  
- Melds allowed as long as tiles meet criteria  
#### 2. Common Wins — 2 Fan Each
**④ All pungs — 2 fan**  
Definition: Hand consists of four pung/kong sets and one pair.  
Requirements:  
- Exposed or concealed allowed  
- Pair may be any tile  
**⑤ Mixed triple chow — 2 fan**  
Definition: Same numbered chow appears in all three suits.  
Example: 4–5–6 in characters, dots, bamboos  
Requirements:  
- Three identical sequences, one in each suit  
#### 3. Advanced Hands — 4–6 Fan Each
**⑥ Pure flush — 4–6 fan**  
Definition: Whole hand uses tiles from one suit, no honors.  
Fan range:  
- Exposed melds → lower (4 fan)  
- Fully concealed → higher (6 fan)  
**⑦ Little dragons — 4–6 fan**  
Definition:  
- Two dragon pungs/kongs  
- Pair made from the remaining dragon  
Requirements:  
- Dragon melds may be exposed or concealed  
- Pair must be the third dragon  
#### 4. Add-on Bonuses — +1 to +2 Fan
**⑧ Kong — +1 fan**  
Definition: Kong formed by upgrading an existing Pung meld (from self-draw or discard).  
Bonus: +1 fan per kong  
**⑨ "Kong open" win — +1 fan**  
Definition: Win on the tile drawn immediately after making a kong.  
Bonus: +1 fan, added on top of kong bonuses  

---

### Pi Hu Rule and Strategy Implications

In our simulation, **Pi Hu with 1 fan is allowed** as the minimum valid winning hand.  
Traditional Beijing rules require at least one fan to declare a win, and our implementation enforces this:  
a structurally complete hand of four melds plus one pair **must have at least 1 fan to win** (0 fan is invalid).  
**Pi Hu (1 fan)** represents the most basic winning hand and is fully allowed.

This creates two key consequences for the simulation:
1. Defensive players can win with **1 fan (Pi Hu)** as soon as they reach this minimum threshold, reducing exposure to deal-in risk.  
2. Aggressive players pursue higher-fan outcomes (typically 3+ fan), choosing to continue drawing rather than accepting 1-fan Pi Hu wins.



---

## 🎯 Hypotheses

**H1:**  
Defensive players, who prioritize winning whenever possible, will achieve higher expected long-term monetary profit than aggressive players, who only win on hands meeting or exceeding a specified fan threshold.

**H2:**  
Despite potentially earning less monetary profit, aggressive players will achieve higher average utility than defensive players when utility accounts for both emotional rewards of large-hand wins and penalties for missed opportunities or deal-ins.

**H3:**  
The relative performance of aggressive and defensive strategies depends on the **composition of opponents** at the table.  
As the proportion of defensive players increases, the expected profit of aggressive players rises, while that of defensive players declines.

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
- **Player Actions:** Players can declare **Peng** (triplet from discard), **Kong** (quad, upgraded from Pung), or **Hu** (win)
- **Chi (sequence) is NOT allowed** in this variant
- **Winning Detection:** Real pattern matching to detect valid winning hands (4 melds + 1 pair)
- **Fan Calculation:** Based on actual hand patterns (triplets, sequences, Kongs, special patterns)

**Scoring:**
Each round yields one or more winning events (self-draw or deal-in win).  
Scoring follows the Beijing Mahjong rule: `Score = B × 2^fan` where `B` is the base unit score and total fan includes bonuses from hand patterns and Kongs.  
Deal-in penalties are subtracted from the losing player's total; self-draws distribute points from all three opponents.  
The **minimum fan requirement** ensures that any hand with `Fan < 1` is invalid and yields no win. **Pi Hu with 1 fan is allowed** and represents the most basic winning hand.

---

### Phase 2 – Experiments

We define two player strategies as decision policies on when to declare a win:

- **Defensive strategy (DEF):** declares Hu immediately when `fan >= fan_min` (typically 1) and the hand is ready; minimizes further risk.  
- **Aggressive strategy (AGG):** declares Hu only if `fan >= t_fan_threshold` (for example, `t_fan_threshold = 3`); otherwise continues drawing, pursuing higher-fan hands.

Each simulation trial consists of **20 rounds per player** (configurable via `rounds_per_trial`), with multiple trials (default: 10) to obtain stable distributions.

| **Experiment** | **Variable Manipulated** | **Purpose** |
|-----------------|--------------------------|-------------|
| 1. Strategy comparison | Compare DEF vs AGG under identical conditions | Test H1 (profit difference) and H2 (utility difference with CRRA utility) |
| 3. Table composition sweep | Vary proportion of DEF players, theta = 0, 0.33, 0.67, 1 | Test H3 (composition threshold) |
| 4. Sensitivity analysis | Vary P (deal-in penalty: [1, 3, 5]), alpha ([0.1, 0.5, 0.9]), fan threshold ([1, 3, 5]), and base points ([1, 2, 4]) | Examine robustness of conclusions across parameter ranges |

**Utility function:**

The utility function uses a concave reward function with penalties. For each round, the utility change is computed as:

```
U_round(profit, fan, missed_hu, deal_in) = {
    sqrt(profit) * 3                    if profit > 0 and fan < 3
    sqrt(profit) * 3 * 2                if profit > 0 and fan >= 3
    -sqrt(|profit|) * 3                 if profit < 0
    0                                    if profit == 0
} - missed_penalty - deal_in_penalty
```

Where:
- `missed_penalty = 0.2` (penalty for missing a possible Hu)
- `deal_in_penalty = 0.5` (penalty for dealing in as loser)
- `fan`: Fan count of the winning hand (used for bonus multiplier when fan >= 3)

**Total utility per trial** is calculated as:
```
U_total = baseline_utility + Σ(U_round for all rounds)
```

Where:
- `baseline_utility = 50` (configurable in `base.yaml`) - starting utility value added to cumulative utility
- Each round's utility change (`U_round`) is computed based on that round's profit and added to the cumulative total

**Key design principles:**
- The square root function (`sqrt`) creates diminishing returns, reflecting that additional profit provides less utility gain
- The base multiplier `* 3` scales the utility to a more representative scale
- High-fan wins (fan >= 3) receive a 2x bonus multiplier, making aggressive strategies potentially more rewarding despite lower win rates
- Penalties are minimal and do not overpower the concave rewards

---

### Phase 3 – Analysis

Simulation outputs are aggregated across all trials to estimate:

- Expected profit per trial: E(Score)  
- Expected utility: E(U)  
- Variance and confidence intervals for both measures  
- Win rate, self-draw rate, and deal-in rate  
- Fan distribution (frequency of 1–16 fan outcomes)  
- Risk metrics such as maximum drawdown and ruin probability under a finite bankroll  

Statistical comparisons between strategy types use **two-sample t-tests** and **confidence intervals**.  
For composition analysis (H3), we run a **regression of profit against theta** (the proportion of defensive opponents) to detect sign changes that indicate the critical threshold of player compositions.  

All experiments use **modular Python code** and configuration-driven runs via YAML inputs.

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

```yaml
base_points: 1              # Base point value for scoring (B in Score = B * 2^fan)
fan_min: 1                  # Minimum fan for defensive strategy (Pi Hu = 1 fan)
t_fan_threshold: 3          # Fan threshold for aggressive strategy
alpha: 0.5                  # Utility weight parameter (currently unused in utility calculation)
penalty_deal_in: 3          # Deal-in penalty multiplier
rounds_per_trial: 20        # Number of rounds per trial
trials: 10                  # Number of trials to run (10-50 is the most optimal,beyond 50 is time consuming)
baseline_utility: 50        # Starting utility value (added to cumulative utility)

```

### Running Experiments

**Run a specific experiment:**
```bash
python main.py --experiment 1    # Strategy comparison
python main.py --experiment 3    # Table composition analysis
python main.py --experiment 4    # Sensitivity analysis
```

**Run all experiments:**
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

**Test coverage:** Currently **65.56%** (exceeds 60% requirement)

---

## 📁 Project Structure

```
597PRFINAL/
├── configs/
│   └── base.yaml              # Configuration file for all experiments
├── experiments/
│   ├── run_experiment_1.py   # Strategy comparison experiment
│   ├── run_experiment_3_table.py  # Table composition analysis
│   └── run_sensitivity.py    # Sensitivity analysis
├── mahjong_sim/
│   ├── __init__.py
│   ├── real_mc.py            # Core Monte Carlo simulation engine
│   ├── scoring.py            # Scoring functions (score, profit, cost)
│   ├── strategies.py         # Strategy functions (defensive/aggressive)
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

## 🧪 Testing

The project includes comprehensive unit tests with **65.56% code coverage** (exceeding the 60% requirement).

**Test files:**
- `test_simulation.py`: Basic simulation functionality
- `test_simulation_extended.py`: Extended tests including utility calculation
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
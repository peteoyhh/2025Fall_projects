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
| 1. Strategy comparison | Compare DEF vs AGG under identical conditions | Test H1 (profit difference) |
| 2. Utility function analysis | Apply nonlinear utility U(score) with CRRA or weighted penalties | Test H2 (utility difference) |
| 3. Table composition sweep | Vary proportion of DEF players, theta = 0, 0.33, 0.67, 1 | Test H3 (composition threshold) |
| 4. Sensitivity analysis | Vary P (deal-in penalty), alpha (fan growth rate), and total fan | Examine robustness of conclusions |

**Utility function:**
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

## 📚 Reference

Chen, J. C., Tang, S. C., & Wu, I. C. (n.d.). *Monte-Carlo simulation for Mahjong.*  
National Yang Ming Chiao Tung University Academic Hub.  
[https://scholar.nycu.edu.tw/en/publications/monte-carlo-simulation-for-mahjong](https://scholar.nycu.edu.tw/en/publications/monte-carlo-simulation-for-mahjong)

*Image from:*  
Chen, J. C., Tang, S. C., & Wu, I. C. (n.d.). *Monte-Carlo simulation for Mahjong.*  
National Yang Ming Chiao Tung University Academic Hub.  
[https://scholar.nycu.edu.tw/en/publications/monte-carlo-simulation-for-mahjong](https://scholar.nycu.edu.tw/en/publications/monte-carlo-simulation-for-mahjong)

---
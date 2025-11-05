# Monte Carlo Simulation of Strategic Trade-offs in Beijing Mahjong

**Authors:** Xu Chen, BoHan Shan  
**NetIDs:** xc74, bohans3  

---

## 🀄 Introduction

Mahjong is a traditional four-player strategy game that blends elements of probability, pattern recognition, and risk–reward decision-making.  
This project focuses on **Beijing-style Mahjong**, a ruleset widely played in northern China.  

Each player begins with **13 tiles** and draws one on each turn, discarding one until achieving a valid **14-tile winning hand (Hu)**.  
A standard winning hand must consist of **four melds (sets)** and **one pair (eyes)**, where melds can be:

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
| **Common wins** | All pungs, Mixed triple chow, Half flush | 2 fan |
| **Advanced hands** | Pure flush, Mixed terminals, Little dragons | 4–6 fan |
| **Top hands** | Big dragons, All honors, Nine gates, Thirteen orphans | 8–13 fan |
| **Add-on bonuses** | Exposed kong +1 fan; Concealed kong +2 fan; “Kong open” win +1 fan | Variable (1–3 fan) |

---

### Pi Hu Rule and Strategy Implications

In Beijing Mahjong, not every completed 14-tile structure qualifies as a winning hand.  
A minimal “empty” hand with no special patterns—called **Pi Hu**—satisfies the structure of four sets plus one pair but **has no fan value**.  
Since at least one fan is required to declare a win, **Pi Hu is not a legal winning hand**.

This rule creates two key strategic consequences:
1. Players must aim for at least one scoring feature (such as Self-draw, Concealed hand, or All simples).  
2. Defensive players often settle for the simplest 1-fan patterns, while aggressive players continue drawing to pursue higher-value combinations.

In simulation terms, the Pi Hu restriction forms a **minimum fan threshold constraint**—hands with fan = 0 are invalid, forcing a tradeoff between chasing higher fan counts and avoiding the risk of losing before completion.

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

Each simulated round represents a complete hand among four players.  
The model generates the following **random variables** for each player in each hand:

| **Variable** | **Meaning** |
|---------------|-------------|
| **Q** | Hand quality (potential to complete a winning hand) |
| **F** | Fan potential (expected hand value if completed) |
| **R** | Deal-in risk (probability of discarding a winning tile) |
| **T** | Threat level (pressure from others being close to win) |
| **K** | Kong events per hand (0–2 typical, adds bonus fan) |

Each round yields one or more winning events (self-draw or discard win).  
Scoring follows the Beijing Mahjong rule:where `B` is the base unit score and total fan includes bonuses from hand patterns and Kongs.  
Deal-in penalties are subtracted from the losing player’s total; self-draws distribute points from all three opponents.  
The **Pi Hu restriction** ensures that any hand with `Fan < 1` is invalid and yields no win.

---

### Phase 2 – Experiments

We define two player strategies as decision policies on when to declare a win:

- **Defensive strategy (DEF):** declares Hu immediately when `F >= 1` and the hand is ready; minimizes further risk.  
- **Aggressive strategy (AGG):** declares Hu only if `F >= Tfan` (for example, `Tfan = 3`); otherwise continues drawing, increasing both `F` and `R`.

Each simulation trial consists of **200 rounds per player** for long-term observation and **20 rounds** for short-term dynamics, with thousands of repetitions to obtain stable distributions.

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

- Expected profit per 200 rounds: E(Score)  
- Expected utility: E(U)  
- Variance and confidence intervals for both measures  
- Win rate, self-draw rate, and deal-in rate  
- Fan distribution (frequency of 1–13 fan outcomes)  
- Risk metrics such as maximum drawdown and ruin probability under a finite bankroll  

Statistical comparisons between strategy types use **two-sample t-tests** and **confidence intervals**.  
For composition analysis (H3), we run a **regression of profit against theta** (the proportion of defensive opponents) to detect sign changes that indicate the critical threshold of player compositions.  

All experiments are conducted under **reproducible random seeds**, using **modular Python code** and configuration-driven runs via YAML or JSON inputs.

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
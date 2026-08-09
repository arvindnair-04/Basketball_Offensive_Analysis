# Basketball Offensive Scouting Dashboard

### Liga ACB 2024–25 | Shooting • Pick-and-Roll • Player Profiling

A reproducible **Streamlit scouting application** built from the provided 2024–25 Spanish basketball season aggregate data.

The dashboard is designed around one central question:

> **How can a scout compare offensive players without being misled by role, workload, shot profile, or small sample sizes?**

**Live App:**  
https://basketballoffensiveanalysis.streamlit.app

---

## Overview

The application supports three stages of a scouting workflow:

1. **Discovery** — identify interesting players across the league.
2. **Contextualization** — understand how those players generate offensive production.
3. **Player Evaluation** — inspect individual strengths, weaknesses, roles, reliability, and comparable players.

The goal is **not to produce one definitive player ranking**, but to provide evidence that helps a scout decide which players deserve further investigation.

---

## Application Pages

### Shooting Analysis

Evaluates players using both **volume and efficiency**.

Features include:

- Interactive metric-vs-metric league scatterplots
- Shooting volume and efficiency leaderboards
- Rim, paint, mid-range, and three-point profiles
- Catch-and-shoot vs. off-dribble analysis
- Contested vs. uncontested shooting
- Blocked-shot vulnerability
- Stabilized zone efficiency
- Shooting-style classifications

Example scouting questions:

```text
Who combines high shooting volume with strong efficiency?

Which players provide reliable floor spacing?

Who creates efficiently off the dribble?

Which players consistently generate rim pressure?
```

---

### Pick-and-Roll Analysis

Separates players into meaningful PnR roles:

```text
Ball Handler
Screener
Dual Role
Low PnR Sample
```

Metrics include:

- Pick volume
- Picks per game
- Points per pick
- Shot rate
- Pass rate
- Assist-opportunity rate
- Turnover rate
- Successful-action rate
- Role-specific percentiles
- Defensive coverage and screen-location splits

Handlers and screeners are evaluated separately because their responsibilities within the same action are fundamentally different.

---

### Player Profile

Combines shooting and pick-and-roll information into an individual scouting profile.

Includes:

- Headline offensive statistics
- League percentile radar
- Player comparison
- Shot diet
- Zone efficiency
- Creation style
- PnR behavior
- Reliability indicators
- Similar-player identification

The page is designed to answer:

> **What type of offensive player is this, and what evidence supports that interpretation?**

---

## Data

The project uses the supplied datasets:

```text
data/
├── season_aggregates/
│   ├── SPAIN_2024-2025_shots_offense.csv
│   └── SPAIN_2024-2025_picks_offense.csv
└── glossary/
    └── metric_glossary.csv
```

The shooting and PnR datasets are joined using `player_id`.

```python
profiles = shots.merge(
    picks,
    on="player_id",
    how="outer",
    suffixes=("", "_pnr"),
    validate="one_to_one"
)
```

### Why an outer join?

Players with valid shooting data but limited PnR involvement should not disappear from the analysis.

### Why `validate="one_to_one"`?

It protects against unexpected duplicate player IDs silently multiplying rows during the merge.

---

# Analytical Approach

## Volume + Efficiency

A core design principle is:

> **Efficiency should not be interpreted without workload.**

For example:

```text
Player A: 4/8 from three = 50%
Player B: 80/200 from three = 40%
```

A raw percentage leaderboard ranks Player A higher despite the much smaller sample.

The dashboard therefore combines:

- raw volume;
- per-game volume;
- efficiency;
- qualification thresholds;
- reliability;
- stabilized estimates.

---

## Key Shooting Metrics

### Effective Field Goal Percentage

```text
eFG% = (FGM + 0.5 × 3PM) / FGA
```

eFG% accounts for the additional value of three-point shots and is therefore more informative than overall FG% when comparing shooting efficiency.

### True Shooting Percentage

TS% incorporates field goals and free throws, providing a broader measure of scoring efficiency.

### Shot Profile

Players are evaluated across:

```text
Rim
Short Mid-Range / Paint
Long Mid-Range
Three-Point Range
```

Both **frequency** and **efficiency** are considered because shot selection and shot-making are different skills.

### Shot Creation

Catch-and-shoot and off-dribble metrics help distinguish players who primarily provide spacing from players with greater self-creation responsibility.

---

## Pick-and-Roll Metrics

PnR analysis combines both production and decision-making.

Important metrics include:

- Points per pick
- Pick volume
- Shot rate
- Pass rate
- Assist-opportunity rate
- Turnover rate

Turnover percentile direction is reversed because:

> **Lower turnover rate represents better performance.**

---

# Sample-Size Handling

Season aggregate data can create misleading extreme percentages when opportunity counts are small.

The application therefore uses configurable minimum thresholds for:

- appearances;
- total attempts;
- shooting-zone attempts;
- catch-and-shoot attempts;
- off-dribble attempts;
- PnR involvement;
- coverage and screen-location samples.

Percentiles are calculated only among players meeting the relevant qualification criteria.

---

## Reliability

Reliability indicators communicate how much observational support exists behind a player's metric.

They should **not** be interpreted as formal confidence intervals or probabilities of true ability.

Instead, they provide a warning when a result is based on limited data.

---

## Stabilized Zone Efficiency

Zone shooting percentages are stabilized toward the league average to reduce the impact of extreme small samples.

Conceptually:

```text
Stabilized FG%
=
(Player Makes + Prior Weight × League FG%)
/
(Player Attempts + Prior Weight)
```

The current implementation uses a **30-attempt prior**.

As sample size increases, the player's observed performance receives more influence.

The prior is a pragmatic analytical choice rather than an empirically optimized parameter.

---

## Shot-Making Over Expected

Stabilized player finishing is compared against league efficiency by shooting zone.

This helps distinguish whether offensive efficiency comes from:

- taking efficient shots;
- finishing above league expectation;
- or both.

This is a **descriptive metric**, not a complete expected-shot model, because the aggregate dataset does not contain defender distance, shot-clock state, player movement, or exact shot coordinates.

---

# Composite Scouting Indicators

The application also contains exploratory profiles such as:

```text
Primary Creator
Floor Spacer
Rim Pressure
Screen-and-Roll Big
Versatile Scorer
```

These scores combine multiple relevant metrics using transparent heuristic weights.

They are intended as:

> **Scouting filters, not predictive models of total player value.**

With richer historical data, these weights could instead be learned or validated using future performance or expert scouting labels.

---

# Data Quality

The analytical pipeline includes:

- Required-column validation
- Safe division
- Missing-value handling
- One-to-one merge validation
- Preservation of players appearing in only one source dataset
- Cached data preparation

Percentage fields remain on their original `0–1` scale internally and are converted to percentage points only for display.

---

# Project Structure

```text
Basketball_Offensive_Analysis/
│
├── app.py
├── analytics.py
├── ui.py
├── usage_tracking.py
├── admin_auth.py
├── requirements.txt
│
├── pages/
│   ├── shooting_analysis.py
│   ├── pick_and_roll_analysis.py
│   ├── player_profiles.py
│   └── admin_analytics.py
│
└── data/
```

---

# Performance

Data preparation uses Streamlit caching so filter changes do not unnecessarily rerun the complete data-processing pipeline.

Cache invalidation also considers changes to the source files.

---

# Running Locally

Clone the repository:

```bash
git clone https://github.com/arvindnair-04/Basketball_Offensive_Analysis.git
cd Basketball_Offensive_Analysis
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

The core analysis is self-contained and requires no external APIs, cloud credentials, or paid services.

---

# Admin Analytics — Bonus Feature

A separate administrator interface tracks product usage, including:

- logins;
- page visits;
- player-profile views;
- comparisons;
- active users;
- sessions;
- popular pages;
- frequently viewed players.

Streamlit reruns are handled so changing a filter is not automatically counted as another page visit.

Administrator credentials should be configured securely and are intentionally not documented in the public README.

---

# Data Limitations

The supplied data contains season-level aggregates rather than possession-level events.

Therefore, the application cannot fully evaluate:

- possession sequences;
- exact PnR decisions;
- detailed shot difficulty;
- defender distance;
- shot-clock pressure;
- exact blocked-shot locations;
- exact spatial relationships between PnR and shooting zones.

The dashboard avoids creating unsupported precision when these variables are unavailable.

---

# Future Development

With possession-level event or tracking data, this project could be extended with:

- Expected shot quality
- PnR decision-quality modelling
- Defensive reaction analysis
- Spacing and driving-lane analysis
- Screen geometry
- Player movement context
- Multi-season reliability modelling

A further product extension could allow scouts to query the dataset using natural language while restricting answers to metrics supported by the available data.

---

# Technology

```text
Python
Pandas
NumPy
Streamlit
Plotly
SQLite
Git / GitHub
```

---

# Final Perspective

The project is designed to move a scout from:

> **"Who has interesting numbers?"**

to:

> **"Why is this player interesting, how do they create offensive value, how reliable is the evidence, and who should I investigate further?"**

That is the central analytical philosophy behind the application.

---

## Author

**Arvind Nair**  
M.S. Computer Science — Rochester Institute of Technology

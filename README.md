# Basketball Offensive Scouting Dashboard

### Liga ACB 2024–25 | Shooting • Pick-and-Roll • Player Profiling

A reproducible **Streamlit scouting application** for exploring season-level offensive shooting and pick-and-roll performance from the supplied **2024–25 Spanish basketball dataset**.

The application is designed around one central scouting problem:

> **How can we identify and compare offensive players without being misled by role, workload, shot profile, or small sample sizes?**

Rather than simply visualizing the supplied CSV columns, the application transforms the aggregate data into interpretable offensive profiles built around:

- Shooting volume
- Scoring efficiency
- Shot location
- Shot creation
- Pick-and-roll involvement
- Pick-and-roll role
- Decision-making
- Sample reliability
- Player archetypes
- Statistical similarity

---

## Live Application

**Streamlit Deployment**

https://basketballoffensiveanalysis.streamlit.app

---

## Project Objective

The objective of this project is to create an analyst-facing tool that supports three stages of a basketball scouting workflow:

### 1. Discovery

Identify players with interesting offensive profiles across the league.

### 2. Contextualization

Understand **how** each player generates their offensive production.

### 3. Player Evaluation

Investigate an individual player's:

- strengths;
- weaknesses;
- offensive role;
- shooting profile;
- pick-and-roll behavior;
- sample reliability;
- league-relative performance;
- statistical peers.

The application therefore focuses on three main analytical questions.

### Shooting

> **Where does a player shoot, how efficiently do they score, and how is that production created?**

### Pick-and-Roll

> **How does a player contribute as a ball handler or screener, and how efficiently do they convert those opportunities?**

### Player Profiling

> **What type of offensive player is this, how does the player compare with qualified league peers, and which players have similar statistical profiles?**

The goal is **not** to produce a single definitive ranking of players.

Instead, the dashboard provides structured evidence that can support a scout or analyst during player investigation.

---

# Application Overview

The application contains four main analyst-facing sections.

---

## Offensive Analysis

The landing page provides league-level context before individual player evaluation.

It summarizes:

- dataset coverage;
- offensive player distributions;
- shooting-style distributions;
- pick-and-roll role distributions;
- offensive workload;
- league-wide player composition.

This page is designed to answer:

> **What does the offensive landscape of the league look like before evaluating an individual player?**

---

# Shooting Analysis

The Shooting Analysis page evaluates players across both **volume and efficiency** rather than ranking shooting percentages in isolation.

The page includes:

- configurable player qualification thresholds;
- interactive league scatterplots;
- shooting-volume leaderboards;
- shooting-efficiency leaderboards;
- shot-zone distribution;
- rim analysis;
- short-mid-range / paint analysis;
- long-mid-range analysis;
- three-point analysis;
- stabilized zone finishing;
- blocked-shot vulnerability;
- contested vs. uncontested shooting;
- catch-and-shoot analysis;
- off-dribble creation;
- shooting-style classification.

The interactive league map allows analysts to independently select the metrics displayed on each axis.

This makes it possible to investigate different scouting questions without building a separate visualization for every hypothesis.

Examples include:

```text
Shot Volume vs True Shooting Percentage

Three-Point Attempt Rate vs Three-Point Efficiency

Rim Frequency vs Rim Finishing

Catch-and-Shoot Efficiency vs Off-Dribble Efficiency
```

---

# Pick-and-Roll Analysis

Pick-and-roll performance is evaluated separately for:

- **Ball Handlers**
- **Screeners**

This distinction is important because the responsibilities and meaningful metrics for each role are different.

The Pick-and-Roll page includes:

- role-specific qualification filters;
- pick volume;
- picks per game;
- points per pick;
- shot rate;
- pass rate;
- assist-opportunity rate;
- turnover rate;
- successful-action rate;
- role-specific percentiles;
- defensive coverage analysis;
- screen-location analysis.

Players are also classified into PnR roles:

```text
Ball Handler
Screener
Dual Role
Low PnR Sample
```

This prevents players with fundamentally different offensive responsibilities from being interpreted as if they belonged to one homogeneous population.

---

# Player Profile

The Player Profile page moves the workflow from **league exploration** to **individual scouting**.

It combines shooting and pick-and-roll information into a single player-level view.

The profile includes:

- headline offensive statistics;
- league percentile radar;
- optional player-to-player comparison;
- shot-diet visualization;
- zone efficiency;
- blocked-shot vulnerability;
- contested/uncontested performance;
- catch-and-shoot creation;
- off-dribble creation;
- pick-and-roll role;
- PnR efficiency;
- decision-making indicators;
- statistical player similarity.

The page is designed to answer:

> **What type of offensive player am I looking at, and what evidence supports that interpretation?**

---

# Data

The supplied project data contains two season-level offensive datasets.

```text
data/
│
├── season_aggregates/
│   ├── SPAIN_2024-2025_shots_offense.csv
│   └── SPAIN_2024-2025_picks_offense.csv
│
└── glossary/
    └── metric_glossary.csv
```

---

## Shooting Data

The shooting dataset contains aggregated player-level information including:

- field-goal attempts;
- field goals made;
- scoring;
- shooting-zone distribution;
- shooting efficiency;
- contested attempts;
- uncontested attempts;
- catch-and-shoot attempts;
- off-dribble attempts;
- blocked attempts.

---

## Pick-and-Roll Data

The pick-and-roll dataset contains aggregate offensive PnR information for players operating as:

- ball handlers;
- screeners;
- or both.

---

# Dataset Integration

The shooting and pick-and-roll datasets are joined using:

```python
player_id
```

An **outer join** is intentionally used so that players appearing in only one dataset are not silently discarded.

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

A player may have a valid shooting profile while recording limited or no pick-and-roll activity.

Using an inner join would remove these players completely from the combined dataset.

An outer join preserves all available offensive information.

### Why `validate="one_to_one"`?

The expected relationship between the two datasets is one record per player.

Merge validation protects against unexpected duplicate player IDs accidentally multiplying rows and producing incorrect statistics.

---

# Analytical Philosophy

The project follows one central principle:

> **Basketball metrics should be interpreted in context.**

A percentage alone does not fully describe player performance.

The dashboard therefore considers several dimensions together:

```text
Volume
   +
Efficiency
   +
Shot Profile
   +
Creation Style
   +
Role
   +
Sample Size
   +
League Context
```

---

# Shooting Volume

## Attempts Per Game

Season totals can partially reflect the number of games played.

Therefore:

```text
Attempts Per Game = Total Attempts / Appearances
```

is used alongside total attempts.

### Why?

Consider two players:

```text
Player A:
300 attempts in 30 games
= 10 attempts/game

Player B:
300 attempts in 15 games
= 20 attempts/game
```

Their season shooting volume is identical, but their offensive responsibility is very different.

Using both total volume and per-game volume provides better context.

---

# Field Goal Percentage

Field Goal Percentage remains useful because it is intuitive and especially informative when evaluating individual shooting zones.

However, overall FG% has an important limitation:

> **Two-point and three-point field goals are treated equally.**

Therefore, additional efficiency metrics are required.

---

# Effective Field Goal Percentage

Effective Field Goal Percentage accounts for the additional scoring value of three-point makes.

```text
eFG% = (FGM + 0.5 × 3PM) / FGA
```

### Why use eFG%?

Consider:

```text
Player A:
5/10 shooting
All two-pointers
FG% = 50%
Points = 10

Player B:
5/10 shooting
All three-pointers
FG% = 50%
Points = 15
```

FG% treats both performances equally.

eFG% recognizes that the second player generated more scoring value from the same number of attempts.

---

# True Shooting Percentage

True Shooting Percentage provides a broader measure of scoring efficiency by incorporating:

- two-point shots;
- three-point shots;
- free throws.

### Why use TS%?

Players generate scoring value in different ways.

Some rely heavily on three-point shooting, while others attack the basket and draw fouls.

TS% provides a more complete scoring-efficiency measure than field-goal percentage alone.

---

# Shot Profile

The dashboard evaluates four main shooting zones:

```text
Rim

Short Mid-Range / Paint

Long Mid-Range

Three-Point Range
```

For each zone, the application separates two questions.

### Frequency

> **How often does the player shoot from this area?**

### Efficiency

> **How successful is the player when shooting from this area?**

This distinction is important because:

> **Shot preference and shot-making ability are different characteristics.**

For example, a player may be an excellent rim finisher but reach the rim very infrequently.

---

# Shot Creation Style

The application distinguishes between:

```text
Catch-and-Shoot

Off-Dribble
```

attempts and efficiency.

### Why?

Overall shooting efficiency does not explain **how shots are created**.

A high catch-and-shoot share can indicate a floor-spacing role.

Strong off-dribble volume and efficiency can indicate greater self-creation responsibility.

Therefore, two players with similar overall efficiency may perform very different offensive roles.

---

# Rim Pressure

Rim pressure is evaluated using a combination of indicators such as:

- rim attempt frequency;
- rim finishing;
- free-throw generation;
- overall offensive workload.

The objective is to distinguish between:

```text
Players who finish efficiently at the rim
```

and

```text
Players who consistently generate pressure toward the basket
```

These are related but different offensive skills.

---

# Blocked-Shot Vulnerability

The dataset contains player-level blocked attempts.

A blocked-shot rate is therefore calculated relative to shooting volume rather than using raw block totals alone.

### Why?

Raw totals are heavily influenced by opportunity.

A player taking 400 shots naturally has more opportunities to be blocked than someone taking 50.

Using a rate provides better context.

---

# Contested vs Uncontested Shooting

Where supported by the supplied data, shooting efficiency is separated into:

```text
Contested Attempts

Uncontested Attempts
```

This provides useful information about player performance under different defensive contexts.

However:

> **Contest status should not be interpreted as a complete shot-difficulty model.**

The dataset does not include variables such as:

- defender distance;
- number of nearby defenders;
- shot-clock pressure;
- release speed;
- player movement.

Two shots labelled as contested may therefore represent very different levels of difficulty.

---

# Pick-and-Roll Metrics

Pick-and-roll analysis is separated by role because ball handlers and screeners perform different functions within the same action.

---

## Pick Volume

Measures how frequently the player participates in pick-and-roll actions.

Volume represents offensive responsibility and opportunity.

---

## Picks Per Game

Provides a workload-adjusted measure of PnR involvement.

```text
Picks Per Game = Total Picks / Appearances
```

---

## Points Per Pick

Measures scoring production relative to pick involvement.

### Why?

Raw points reward players simply for receiving more opportunities.

Points per pick complements volume by providing an efficiency measure.

---

## Shot Rate

Measures how frequently the player ends the pick action with a shot.

This can help distinguish:

```text
Scoring-oriented handlers
```

from

```text
Pass-oriented creators
```

---

## Pass Rate

Measures how frequently a ball handler distributes the ball rather than directly finishing the action.

This contributes to understanding a player's PnR decision-making style.

---

## Assist-Opportunity Rate

Provides information about how frequently the player creates potential scoring opportunities for teammates.

### Why use it?

Scoring efficiency alone cannot fully describe offensive creation.

A player may generate significant value through passing even when they do not record the final shot.

---

## Turnover Rate

Turnover rate represents possession risk.

Unlike most offensive metrics:

> **Lower turnover rate is better.**

Therefore, percentile calculations involving turnover performance reverse the direction so that better ball security receives the higher percentile.

---

## Successful-Action Rate

Successful-action rate provides another indicator of how frequently positive outcomes occur during pick-and-roll actions.

It is considered alongside efficiency and workload rather than replacing either.

---

# Volume vs Efficiency

One of the core analytical principles of the project is:

> **Efficiency should not be interpreted without volume.**

Consider:

```text
Player A:
4/8 from three
50%

Player B:
80/200 from three
40%
```

A simple three-point percentage leaderboard ranks Player A higher.

However, there is substantially more evidence supporting Player B's percentage.

The dashboard addresses this through:

1. qualification thresholds;
2. volume metrics;
3. rate metrics;
4. percentile eligibility;
5. reliability indicators;
6. stabilized shooting estimates.

---

# Sample-Size Handling

Because the dataset contains season-level aggregates, percentages based on limited opportunities can become misleading.

The application therefore includes configurable minimum thresholds for:

- appearances;
- total field-goal attempts;
- zone attempts;
- catch-and-shoot attempts;
- off-dribble attempts;
- pick-and-roll involvement;
- defensive coverage samples;
- screen-location samples.

Low-volume players can remain visible where useful, but they are not automatically treated as equally reliable comparisons with established high-volume players.

---

# Qualified Percentiles

Percentiles are calculated only among players who satisfy the qualification criteria for the relevant metric.

### Why?

Consider:

```text
Player A:
3/5 from three
60%

Player B:
90/220 from three
40.9%
```

Without qualification thresholds, Player A may receive an elite three-point percentile despite having only five attempts.

The application therefore uses metric-specific eligibility rules.

Different metrics require different underlying event counts.

---

# Reliability

The application includes sample-reliability indicators based on relevant opportunity counts.

Reliability is intended to answer:

> **How much observational support exists behind this player's metric?**

Reliability should **not** be interpreted as:

- a confidence interval;
- statistical significance;
- probability that the metric represents true ability.

Instead, it acts as an intuitive warning when performance is based on limited observations.

---

# Stabilized Zone Finishing

Raw shooting percentages can be unstable for players with limited attempts.

To reduce extreme small-sample estimates, zone efficiency is stabilized toward the league-average shooting percentage for that zone.

Conceptually:

```text
Stabilized FG%

=

(Player Makes + Prior Weight × League FG%)

/

(Player Attempts + Prior Weight)
```

The current implementation uses a:

```text
30-attempt prior
```

---

## Why Stabilize Shooting Percentage?

Consider:

```text
Player A:
3 / 4 at the rim
75%

Player B:
120 / 200 at the rim
60%
```

A raw leaderboard suggests Player A is the superior finisher.

However, four attempts provide very little evidence.

Stabilization moves small samples closer to the league average.

As attempt volume increases, the player's observed percentage receives progressively more influence.

---

## Prior Assumption

The 30-attempt prior is a pragmatic analytical choice rather than an empirically optimized parameter.

With multiple seasons of player data, the prior could instead be estimated using:

- historical metric stability;
- year-to-year correlations;
- predictive performance;
- cross-validation.

---

# Shot-Making Over Expected

The application compares stabilized player zone efficiency with the corresponding league expectation.

Conceptually:

```text
Shot-Making Over Expected

=

Observed / Stabilized Player Efficiency

-

League Expected Efficiency
```

### Purpose

Two players can have similar overall FG% while taking very different shot distributions.

This comparison adds context about whether a player's performance comes primarily from:

```text
Efficient shot selection
```

or

```text
Above-average finishing
```

or

```text
A combination of both
```

---

## Important Limitation

This metric should be interpreted as a **descriptive shot-making indicator**, not a complete expected-shot model.

The aggregate dataset does not contain:

- defender distance;
- shot clock;
- movement state;
- pass type;
- possession sequence;
- detailed shot coordinates.

Therefore, "expected" refers to the available shooting-zone context rather than full shot difficulty.

---

# Offensive Style Labels

Players are assigned descriptive offensive-style labels using combinations of observed metrics.

These classifications are designed to make the player pool easier for scouts to explore.

They should be interpreted as:

> **Descriptive summaries rather than definitive positions or machine-learned archetypes.**

The objective is to help identify players with similar headline numbers but different offensive behaviors.

---

# Role-Specific Percentiles

Percentile comparisons are calculated within meaningful offensive populations.

Examples:

```text
Ball-handler creation metrics
→ compared with qualified handlers

Screener metrics
→ compared with qualified screeners

Shooting metrics
→ compared with qualified shooters
```

### Why?

A percentile is only meaningful when the comparison population is meaningful.

Comparing a low-volume screener with a primary ball handler on identical creation metrics would provide limited scouting value.

---

# Player Similarity

The Player Profile page identifies statistical neighbors using shared percentile dimensions.

A minimum number of shared dimensions is required before similarity is calculated.

### Purpose

Player similarity is intended as a **scouting discovery tool**.

It helps answer:

> **Which players have a similar offensive statistical profile?**

This can help scouts identify:

- comparable players;
- alternative recruitment targets;
- potential role replacements;
- similar offensive archetypes.

However:

> Statistical similarity does not necessarily mean tactical or stylistic equivalence.

Video analysis and contextual scouting remain necessary.

---

# Composite Scouting Scores

The application includes several exploratory role-fit or composite indicators.

Examples include profiles oriented toward:

```text
Primary Creator

Floor Spacer

Rim Pressure

Screen-and-Roll Big

Versatile Scorer
```

These indicators combine multiple metrics using explicit heuristic weights.

---

## Why Use Composite Scores?

Basketball scouting often involves multi-dimensional questions.

For example:

> **Which players could function as primary creators?**

A single statistic cannot fully answer that question.

A primary-creator profile may therefore consider:

- PnR creation;
- PnR workload;
- shooting volume;
- off-dribble efficiency;
- turnover control.

---

## Important Interpretation

The composite scores are:

> **Scouting aids, not predictive player-value models.**

The weights are transparent analytical assumptions.

They are **not learned from labelled outcomes**.

With richer historical data, the weights could instead be:

- validated against future performance;
- optimized using predictive models;
- calibrated using expert scouting labels;
- customized to a team's tactical philosophy.

The current implementation keeps these assumptions explicit rather than presenting heuristic scores as objective truths.

---

# Percentage Convention

Percentage and rate fields from the source data are stored internally as values between:

```text
0 and 1
```

For example:

```text
0.382
```

represents:

```text
38.2%
```

Internally, metrics remain on the original `0–1` scale.

They are converted to percentage points only for display.

### Why?

This prevents repeated transformations and reduces the risk of accidentally mixing:

```text
0.38
```

with:

```text
38
```

during calculations.

---

# Data Quality and Defensive Programming

Several safeguards are included in the analytical pipeline.

---

## Required-Column Validation

Expected source fields are checked before transformations are performed.

If required columns are missing, the application raises an explicit error instead of silently producing incomplete analysis.

---

## Safe Division

Rate calculations protect against zero denominators.

Invalid divisions produce missing values rather than:

```text
Infinity
```

or misleading zeros.

---

## Join Validation

The shooting and pick-and-roll datasets use:

```python
validate="one_to_one"
```

during the merge.

This protects against duplicated identifiers accidentally multiplying player records.

---

## Missing Cross-Dataset Players

An outer join preserves players appearing in only one source dataset.

This ensures that:

```text
No PnR record
```

does not automatically mean:

```text
Remove player from shooting analysis
```

and vice versa.

---

# Project Architecture

The application separates analytics from Streamlit presentation logic.

```text
Basketball_Offensive_Analysis/
│
├── app.py
│
├── analytics.py
├── ui.py
├── usage_tracking.py
├── admin_auth.py
├── requirements.txt
├── README.md
│
├── pages/
│   ├── shooting_analysis.py
│   ├── pick_and_roll_analysis.py
│   ├── player_profiles.py
│   └── admin_analytics.py
│
└── data/
    ├── season_aggregates/
    │   ├── SPAIN_2024-2025_shots_offense.csv
    │   └── SPAIN_2024-2025_picks_offense.csv
    │
    └── glossary/
        └── metric_glossary.csv
```

---

# Module Responsibilities

## `analytics.py`

Responsible for:

- loading datasets;
- required-column validation;
- data cleaning;
- derived metrics;
- safe rate calculations;
- sample-size rules;
- percentile calculations;
- reliability;
- stabilized shooting;
- offensive classifications;
- player similarity;
- composite scouting indicators.

---

## `pages/`

Contains the analyst-facing Streamlit views.

Separating analytical transformations from UI code reduces duplication and improves maintainability.

---

## `ui.py`

Contains reusable interface and presentation components.

---

## `usage_tracking.py`

Handles local user-product interaction events for the optional administrator analytics system.

---

## `admin_auth.py`

Contains the authentication logic associated with the administrator prototype.

---

# Performance

Streamlit reruns the Python application whenever the user interacts with a widget.

To avoid repeatedly processing the same source data, data preparation is cached.

Caching improves responsiveness for actions such as:

- changing qualification thresholds;
- selecting players;
- changing teams;
- modifying chart variables;
- changing filters.

The cache also considers source-file modification timestamps so updated data can invalidate previously cached transformations.

---

# Installation

## Requirements

- Python 3.10+
- pip

---

## Clone Repository

```bash
git clone https://github.com/arvindnair-04/Basketball_Offensive_Analysis.git
cd Basketball_Offensive_Analysis
```

---

## Create Virtual Environment

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run Application

```bash
streamlit run app.py
```

The application is self-contained.

The core analytical application does **not** require:

- external APIs;
- cloud credentials;
- paid services;
- external analytical databases.

---

# Authentication

The application contains a lightweight local authentication system.

Users can create an account from the application interface.

Authentication data is stored using a local SQLite database.

The authentication functionality primarily supports the optional administrator product-analytics prototype while keeping the project self-contained.

---

## Production Consideration

The local authentication system is a prototype.

For a production environment, user authentication and persistence should be moved to a secure external identity and database service.

Administrator passwords or other secrets should **not** be committed to the public repository.

Potential production approaches include:

- environment variables;
- Streamlit Secrets;
- managed authentication providers;
- external databases.

---

# Administrator Usage Analytics — Bonus Feature

A separate administrator analytics interface was developed to explore how users interact with the scouting product.

Tracked events include:

- successful login;
- logout;
- navigation between analytical pages;
- player-profile views;
- player-comparison selections.

The administrator dashboard can analyze:

- registered users;
- active users;
- sessions;
- page visits;
- page popularity;
- frequently viewed players;
- daily activity;
- user-by-page usage;
- recent activity.

---

# Handling Streamlit Reruns

Streamlit reruns the application script whenever a user interacts with a widget.

For example:

```text
Changing minimum attempts
```

causes a rerun.

However, this should **not** automatically be interpreted as another page visit.

The usage-tracking implementation therefore de-duplicates page-view events to better distinguish:

```text
Actual navigation
```

from:

```text
Streamlit reruns
```

This improves the usefulness of the product-engagement analytics.

---

# Data Limitations

The dashboard is deliberately constrained by what can be supported by the supplied season-level aggregate datasets.

---

## 1. No Possession-Level Sequences

The data contains aggregated season statistics rather than individual possession events.

Therefore, the dashboard can analyze:

- where players shoot;
- how frequently they shoot;
- how efficiently they shoot;
- aggregate PnR behavior;
- season-level offensive tendencies.

It cannot reconstruct the exact sequence of decisions within an individual possession.

---

## 2. Contest Does Not Fully Measure Shot Difficulty

The dataset contains contested and uncontested classifications.

It does not contain:

- defender distance;
- number of nearby defenders;
- shot-clock pressure;
- release speed;
- shooter movement.

Therefore:

> **Contested vs uncontested should be interpreted as contextual information rather than a complete shot-quality model.**

---

## 3. Blocked Shots Are Player-Level Totals

Blocked attempts are available at player level.

The dataset does not provide exact shooting-zone locations for every blocked attempt.

Therefore, the application does **not** fabricate zone-level blocked-shot information.

---

## 4. PnR Attempts Cannot Be Perfectly Mapped to Shooting Zones

Pick-and-roll shooting data distinguishes broader shot categories.

The shooting dataset contains more detailed zones such as:

```text
Rim
Short Mid-Range / Paint
Long Mid-Range
Three
```

The exact detailed location of each aggregate pick-and-roll two-point attempt cannot therefore be reconstructed.

---

## 5. Statistical Association Is Not Causation

The dashboard describes observed offensive performance.

For example:

```text
A player performs well on contested attempts
```

does not prove:

```text
The player is inherently better under defensive pressure
```

Additional contextual, longitudinal and possession-level data would be necessary for causal claims.

---

# What I Would Add With Richer Data

With possession-level event or tracking data, the project could be expanded substantially.

---

## Expected Shot Quality

A shot-quality model could include:

- exact location;
- defender distance;
- shot-clock state;
- shooter movement;
- pass type;
- possession context;
- player identity.

---

## Pick-and-Roll Decision Quality

Possession sequences could evaluate whether the handler:

- shot;
- passed;
- rejected the screen;
- used the screen;
- attacked the rim;
- found the roller;
- found the popper;
- created an advantage;
- turned the ball over.

---

## Spatial Analysis

Tracking data could support analysis of:

- offensive spacing;
- driving lanes;
- defensive collapse;
- screen geometry;
- separation created;
- defensive rotations;
- off-ball gravity.

---

## Longitudinal Reliability

Multiple seasons could be used to estimate:

- metric stability;
- optimal shrinkage strength;
- predictive reliability;
- player-development trajectories.

---

# Future Product Development

A potential extension is an **AI-assisted basketball analytics interface**.

This would allow analysts to query the available data using natural language.

Example requests:

```text
Show high-volume shooters with above-average true shooting.
```

```text
Find ball handlers with strong PnR efficiency and low turnover rates.
```

```text
Compare this player's rim, mid-range and three-point usage.
```

```text
Which players have a similar offensive profile?
```

The assistant would be restricted to calculations supported by the available dataset.

It would:

1. identify relevant variables;
2. check whether the requested analysis is possible;
3. apply sample-size rules;
4. perform the analysis;
5. generate an appropriate visualization;
6. explain assumptions;
7. flag unsupported requests.

The objective would be to improve analytical accessibility without sacrificing methodological transparency.

---
# Technology Stack

The project uses:

```text
Python
Pandas
NumPy
Streamlit
Plotly
SQLite
Git
GitHub
```

---

# Reproducibility

The analytical application can be reproduced with:

```bash
pip install -r requirements.txt
streamlit run app.py
```

All analytical data required for the assignment is included locally.

The core scouting application requires no external APIs or cloud services.

---


# Final Perspective

The objective of this project is **not** to identify the "best" offensive player using one number.

Instead, it attempts to make player evaluation more structured.

The dashboard helps move the analyst from:

> **"Who has interesting numbers?"**

toward:

> **"Why is this player interesting, how do they create offensive value, how reliable is the evidence, and who should I investigate further?"**

That distinction is the central analytical philosophy behind the project.

---

# Author

**Arvind Nair**

M.S. Computer Science  
Rochester Institute of Technology

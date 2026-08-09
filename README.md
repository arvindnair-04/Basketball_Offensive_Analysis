# Basketball Offensive Scouting Dashboard — Liga ACB 2024–25

A self-contained Streamlit application for exploring the supplied 2024–25 Spanish season offensive shooting and pick-and-roll aggregates.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Create a local account from the opening screen and sign in. Authentication uses the included local SQLite `users.db`; no external APIs, cloud credentials or remote databases are required.

## Navigation

- **Overview** — `Offensive Analysis`: explains what is being analyzed, summarizes dataset coverage, shows league shooting-style/PnR-role distributions, and provides workload context.
- **Shooting Analysis** — configurable league map, leaderboards, league-wide zone distribution, qualified high-value producers by zone, zone reliance vs blocked-shot rate, contested/uncontested efficiency, and catch-vs-dribble creation.
- **Pick-and-Roll Analysis** — separate ball-handler/screener filters, leaderboards, league-wide defensive coverage analysis, and league-wide screen-location analysis.
- **Player Profile** — player statistics, league percentile radar and optional direct comparison, shot-diet wheel + efficiency, observed blocked-shot vulnerability, role-specific PnR decision behavior, success/turnover rates, and nearest statistical neighbors.

## Percentage convention

The source files store percentage/rate fields as ratios from 0 to 1. In the application, displayed percentages are converted to percentage points by multiplying by 100 and are rounded to two decimal places. Underlying ratios remain unchanged inside the analytics calculations.

## Sample handling

The interface exposes minimum appearance, shooting-attempt, pick, coverage and screen-location thresholds. These prevent tiny samples from being presented as if they were directly comparable with high-volume players.

The shared `analytics.py` layer also computes per-game volume, true shooting, free-throw and block rates, shot-style labels, PnR role labels, qualified league percentiles, sample-reliability scores, stabilized zone finishing, and nearest statistical comparisons.

## Important data limitations

The dashboard is built from season-level shooting and pick-and-roll aggregates, so the analysis is strongest for describing **where players shoot, how efficiently they score, how often they are blocked, and how they perform in different pick-and-roll situations**. The following limitations should be considered when interpreting those results:

- The shooting analysis includes **contested and uncontested efficiency**, but it does not include the **time pressure of the shot**. Two attempts may both be classified as contested even though one player had time to set their feet while another had to release immediately. The dashboard therefore measures defensive contest context, but not how quickly the player had to make the shooting decision.
- The data includes whether shooting attempts were **blocked** and provides overall blocked-shot totals for each player, but it does not include the **number of defenders or blockers involved around the shot**. As a result, the blocked-shot analysis can show how often a player's attempts are blocked relative to their shooting volume, but it cannot distinguish between pressure from one defender and situations where multiple defenders collapse on the shooter.
- Blocked shots are available as an **overall player-level total**, not as observed blocked shots for each shooting zone. The dashboard therefore uses the player's real blocked-shot total when evaluating blocked-shot vulnerability, but does not assign blocked shots to the rim, short mid-range, long mid-range or three-point zones.
- The dashboard uses shooting zones such as **rim, short mid-range/paint, long mid-range and three-point range** to describe a player's general shot diet. Pick-and-roll shooting, however, is represented as **2PT versus 3PT behavior**, so the exact two-point location of a pick-and-roll shot cannot be tied directly to the more detailed shooting-zone breakdown.
- The dataset is made up of **season aggregates rather than possession-by-possession or frame-by-frame events**. Metrics such as true shooting percentage, effective field-goal percentage, shot-zone efficiency, pick-and-roll points per pick, success rate and turnover rate therefore summarize the player's season-level performance rather than the exact sequence of decisions within an individual possession.

## Future work

A planned extension of the dashboard is an **AI-assisted analytics chatbot** that allows coaches and analysts to create their own visualizations using natural-language questions. Instead of being limited to the predefined charts in the dashboard, a user could ask questions such as *“compare high-volume shooters by true shooting percentage,”* *“show ball handlers with high pick-and-roll efficiency and low turnover rates,”* or *“compare a player's rim, mid-range and three-point usage.”*

The chatbot would be restricted to the variables available in the supplied datasets and to metrics that can be calculated reliably from those variables. It would interpret the user's request, identify the relevant fields or derived metrics, apply appropriate filters or minimum-sample rules, and generate a suitable chart automatically. This would make the dashboard more flexible for experienced analysts while also allowing less technical users to explore the data without needing to write Python or manually configure every graph.

A longer-term goal is for the chatbot to act as an **interactive analysis layer** rather than simply a chart generator. It could explain which variables were used, flag when a requested analysis is not supported by the available data, suggest an alternative that can be calculated, and help users move from an initial question to a more useful basketball-specific comparison.

## Data coverage

The supplied files contain 295 shooting rows and 292 pick-and-roll rows. They join by `player_id` into 299 unique player profiles, with 288 players appearing in both files and 18 teams represented.

## Admin usage analytics

The application includes an administrator-only **Admin Analytics** interface. Administrator authentication is separate from normal user accounts and is accessed through the **Administrator Login** option on the application's opening login screen. Normal registered users do not see or have access to the Admin Analytics interface.

Usage events are stored locally in the same SQLite database (`users.db`) so the application remains self-contained. The tracker records:

- successful login and logout events;
- navigation between Overview, Shooting Analysis, Pick-and-Roll Analysis and Player Profile;
- primary player-profile lookups;
- player-comparison selections.

The Admin Analytics page summarizes registered and active users, sessions, page visits, player lookups, page popularity, frequently viewed players, daily usage, a user-by-page heatmap, individual user behavior and recent activity. Administrator activity is excluded by default so development/testing traffic does not distort usage patterns.

Page views are de-duplicated across Streamlit widget reruns: an event is recorded when the user navigates to a different page, rather than whenever a filter causes the script to rerun. Player views are similarly recorded only when the selected primary player changes.


## Administrator access

The scouting dashboard and administrator analytics interface run from the same Streamlit application:

```bash
streamlit run app.py
```

Default local prototype administrator credentials:

- Username: `admin`
- Password: `Admin@123`


The admin dashboard does not fabricate activity. If no scout has used the normal application after tracking was added, registered users will still be visible but page/player charts will correctly show that no events have been recorded.


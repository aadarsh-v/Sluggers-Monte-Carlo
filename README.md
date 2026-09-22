# Sluggers Monte Carlo

This repo is a simplified Monte Carlo baseball sim built for a CPU vs. CPU Mario Super Sluggers leauge (that me and my friends are participating in). Players are modeled using the game statistics collected and used to simulate games/seasons. The game and match simulation data is used to support odds/props along with team and player projections.

If you want to run this for your own CPU vs. CPU league, you'll want to collect stats in a similar way to how the stats are collected in the stats sheets (the `data/*.xlsx` files), and modify the team data in the two different scripts to fit your league. These scripts are the following:
- `game_simulation.py`, which simulates a single game between two teams. 
- `season_simulation.py`, which runs a season-long simulation based on the remaining unplayed games in the season.

## What Can This Project Do?

- Simulate individual baseball games with player-level outcomes
- Project full-season standings and (conditional) team/player-level outcomes
- Model hitter and pitcher performance using league baselines and stadium modifiers
- Allows comparison teams and players across repeated Monte Carlo trials
- Produce easy to inspect analysis outputs

## Repo Structure

### Scripts

- `game_simulation.py`  
  Runs a single matchup simulation.

- `season_simulation.py`  
  Runs a season-long Monte Carlo simulation.

### Models

- `models/player.py`  
  Defines a player object, including batting, pitching, and fielding metrics.

- `models/team.py`  
  Builds a roster, lineup, and pitching rotation for a simulated team.

- `models/game.py`  
  Runs in-game logic for innings, batters, pitchers, and event generation.

- `models/simulation.py`  
  Runs Monte Carlo trials for a matchup and aggregates win rates, run totals, hit totals, and per-player averages.

### Data and model inputs

- `data/league_stats.py`  
  League averages and stadium modifiers that are used for model prediction. Stadium modifiers are heuristically obtained due to a lack of data.

- `data/*.xlsx`  
  Raw roster and season data used to initialize teams and drive the simulation.

### Utilities

- `utils/math_utils.py`  
  Regression and matchup math helpers for simulation logic.

- `utils/analysis_utils.py`  
  Odds, formatting, and analysis helpers for standings and player props.

### Outputs and analysis

- `pickles/`  
  Cached simulation results and season outputs.

- `match_analysis.ipynb` and `season_analysis.ipynb`  
  Notebook workflows for digging into game/season results, player leaders, and odds-style summaries.
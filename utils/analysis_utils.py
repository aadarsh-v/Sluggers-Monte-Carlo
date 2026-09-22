from collections import Counter
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- Formatting Methods ---
def prob_to_odds(prob):
    if prob <= 0.0:
        return 100000
    if prob >= 1.0:
        return -100000
    
    if prob > 0.5:
        return -int((prob / (1 - prob)) * 100)
    else:
        return int(((1 - prob) / prob) * 100)    

def round_odds(odds):
    if -113 <= odds <= -107:
        return -110
        
    abs_odds = abs(odds)
    
    if abs_odds < 200:
        step = 5
    elif abs_odds < 1000:
        step = 10
    else:
        step = 50
        
    rounded_abs = int(round(abs_odds / step) * step)
    if rounded_abs == 0:
        rounded_abs = step
        
    return -rounded_abs if odds < 0 else rounded_abs

def format_odds_string(odds):
    return f"+{odds}" if odds > 0 else str(odds)

class SluggerGameOddsAnalyzer:
    """
    Analyzer class for game and player prop simulations for (fictional) sports betting lines.
    Incorporates automated line generation for display (to paste into an Excel sheet).
    """
    
    def __init__(self, data, market_edge=0.05):
        self.data = data
        self.market_edge = market_edge
        self.results = data.get("last_results", {})
        self.player_results = data.get("results", {})
        self.trials = len(self.results.get("total_runs", [])) if self.results else 0

    # --- Automatic Line Calculators ---

    @staticmethod
    def find_optimal_half_line(stat_list, trials):
        """Finds the .5 line that brings the Over True Prob closest to 0.50."""
        candidate_lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 14.5, 16.5]
        best_line = 0.5
        best_diff = float('inf')
        
        for line in candidate_lines:
            over_count = sum(1 for val in stat_list if val > line)
            over_prob = over_count / trials
            
            if over_prob == 0:
                continue
                
            diff = abs(over_prob - 0.50)
            if diff < best_diff:
                best_diff = diff
                best_line = line
                
        return best_line

    @staticmethod
    def calculate_auto_game_line(stat_list):
        """Automatically calculates a clean .5 game total or team line using the median simulation value."""
        if not stat_list:
            return 10.5
        median_val = np.median(stat_list)
        line = round(median_val * 2) / 2
        if line % 1 == 0:
            line += 0.5
        return line

    def calculate_auto_spread_line(self):
        """Automatically calculates the run line spread based on the median run differential."""
        home_runs = self.results.get("home_runs", [])
        away_runs = self.results.get("away_runs", [])
        if not home_runs or not away_runs:
            return 3.5
        margins = [h - a for h, a in zip(home_runs, away_runs)]
        median_margin = np.median(margins)
        line = round(median_margin * 2) / 2
        if line % 1 == 0:
            line += 0.5
        if line < 0 and abs(line) < 1:
            line = -1.5
        if line > 0 and line < 1:
            line = 1.5
        return line

    # --- Player/Team Odds Helpers ---

    def get_team_game_odds(self, metric_key, line_value):
        """
        Calculates over/under odds and probabilities for total game metrics (e.g., total runs) 
        or team-specific stats based on simulation trial runs.
        """
        results = self.results

        # If it's a total metric like 'total_runs' or 'total_hits'
        if metric_key.startswith("total_"):
            trial_list = results.get(metric_key, [])
            if not trial_list:
                return pd.DataFrame()
                
            over_count = sum(1 for x in trial_list if x > line_value)
            under_count = sum(1 for x in trial_list if x < line_value)
            push_count = sum(1 for x in trial_list if x == line_value)
            
            over_raw_prob = over_count / self.trials
            under_raw_prob = under_count / self.trials
            push_raw_prob = push_count / self.trials
            
            over_adj_prob = min(over_raw_prob * (1 + self.market_edge), 0.9999)
            under_adj_prob = min(under_raw_prob * (1 + self.market_edge), 0.9999)
            
            df = pd.DataFrame([{
                "Market": f"Game {metric_key.replace('_', ' ').title()}",
                "Line": f"O/U {line_value}",
                "Over True Prob": over_raw_prob,
                "Over Adj Prob": over_adj_prob,
                "Under True Prob": under_raw_prob,
                "Under Adj Prob": under_adj_prob,
                "Push %": (push_raw_prob * 100)
            }])
        else:
            # Team-specific metrics (e.g., home_runs, away_hits)
            records = []
            for team_name, key_name in [
                (self.data["home_team"], f"home_{metric_key}"),
                (self.data["away_team"], f"away_{metric_key}")
            ]:
                stats = results.get(key_name, [])
                if not stats:
                    continue
                    
                over_count = sum(1 for x in stats if x > line_value)
                under_count = sum(1 for x in stats if x < line_value)
                push_count = sum(1 for x in stats if x == line_value)
                
                over_raw_prob = over_count / self.trials
                under_raw_prob = under_count / self.trials
                push_raw_prob = push_count / self.trials
                
                records.append({
                    "Team": team_name,
                    "Line": f"O/U {line_value}",
                    "Over True Prob": over_raw_prob,
                    "Over Adj Prob": min(over_raw_prob * (1 + self.market_edge), 0.9999),
                    "Under True Prob": under_raw_prob,
                    "Under Adj Prob": min(under_raw_prob * (1 + self.market_edge), 0.9999),
                    "Push %": (push_raw_prob * 100)
                })
            df = pd.DataFrame(records)

        if df.empty:
            return df

        df = df.sort_values(by="Over True Prob", ascending=False).reset_index(drop=True)
        
        df["Over Fair Odds"] = df["Over True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Over Market Odds"] = df["Over Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Over Implied Prob"] = (df["Over True Prob"] * 100).round(1).astype(str) + "%"

        df["Under Fair Odds"] = df["Under True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Under Market Odds"] = df["Under Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Under Implied Prob"] = (df["Under True Prob"] * 100).round(1).astype(str) + "%"
        
        df["Push Prob"] = df["Push %"].round(1).astype(str) + "%"
        
        display_cols = [c for c in ["Team", "Market", "Line", "Over Implied Prob", "Over Market Odds", "Under Implied Prob", "Under Market Odds", "Push Prob"] if c in df.columns]
        return df[display_cols]

    def get_player_prop_odds(self, stat_key, line_value):
        """
        Calculates over/under prop betting odds and probabilities for individual batters 
        across specific statistical categories based on simulation trial runs.
        """
        player_trials = self.player_results.get("player_trials", {})
        records = []
        
        for player_name, metrics in player_trials.items():
            stat_list = metrics.get(stat_key, [])
            if not stat_list:
                continue
                
            over_count = sum(1 for val in stat_list if val > line_value)
            under_count = sum(1 for val in stat_list if val < line_value)
            push_count = sum(1 for val in stat_list if val == line_value)
            
            over_raw_prob = over_count / self.trials
            under_raw_prob = under_count / self.trials
            push_raw_prob = push_count / self.trials
            
            # Apply market edge / vig safely
            over_adj_prob = min(over_raw_prob * (1 + self.market_edge), 0.985)
            under_adj_prob = min(under_raw_prob * (1 + self.market_edge), 0.985)
            
            records.append({
                "Player": player_name,
                "Line": f"O/U {line_value} {stat_key.upper()}",
                "Over True Prob": over_raw_prob,
                "Over Adj Prob": over_adj_prob,
                "Under True Prob": under_raw_prob,
                "Under Adj Prob": under_adj_prob,
                "Push %": (push_raw_prob * 100)
            })

        df = pd.DataFrame(records)
        if df.empty:
            return df

        df = df.sort_values(by="Over True Prob", ascending=False).reset_index(drop=True)
        
        # Format Odds & Probabilities using helper functions
        df["Over Fair Odds"] = df["Over True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Over Market Odds"] = df["Over Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Over Implied Prob"] = (df["Over True Prob"] * 100).round(1).astype(str) + "%"

        df["Under Fair Odds"] = df["Under True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Under Market Odds"] = df["Under Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Under Implied Prob"] = (df["Under True Prob"] * 100).round(1).astype(str) + "%"
        
        df["Push Prob"] = df["Push %"].round(1).astype(str) + "%"
        
        return df[[
            "Player", "Line", 
            "Over Implied Prob", "Over Market Odds", 
            "Under Implied Prob", "Under Market Odds", "Push Prob"
        ]]

    def get_pitcher_prop_odds(self, stat_key, line_value):
        """
        Calculates over/under prop betting odds and probabilities for individual pitchers 
        who participated in simulation trials.
        """
        player_trials = self.player_results.get("player_trials", {})
        records = []
        
        for player_name, metrics in player_trials.items():
            stat_list = metrics.get(stat_key, [])
            # Only include players who actually pitched in simulations
            if not stat_list or sum(stat_list) == 0:
                continue
                
            over_count = sum(1 for val in stat_list if val > line_value)
            under_count = sum(1 for val in stat_list if val < line_value)
            push_count = sum(1 for val in stat_list if val == line_value)
            
            over_raw_prob = over_count / self.trials
            under_raw_prob = under_count / self.trials
            push_raw_prob = push_count / self.trials
            
            over_adj_prob = min(over_raw_prob * (1 + self.market_edge), 0.9999)
            under_adj_prob = min(under_raw_prob * (1 + self.market_edge), 0.9999)
            
            records.append({
                "Pitcher": player_name,
                "Line": f"O/U {line_value} {stat_key.replace('_', ' ').upper()}",
                "Over True Prob": over_raw_prob,
                "Over Adj Prob": over_adj_prob,
                "Under True Prob": under_raw_prob,
                "Under Adj Prob": under_adj_prob,
                "Push %": (push_raw_prob * 100)
            })

        df = pd.DataFrame(records)
        if df.empty:
            return df

        df = df.sort_values(by="Over True Prob", ascending=False).reset_index(drop=True)
        
        df["Over Fair Odds"] = df["Over True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Over Market Odds"] = df["Over Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Over Implied Prob"] = (df["Over True Prob"] * 100).round(1).astype(str) + "%"

        df["Under Fair Odds"] = df["Under True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Under Market Odds"] = df["Under Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Under Implied Prob"] = (df["Under True Prob"] * 100).round(1).astype(str) + "%"
        
        df["Push Prob"] = df["Push %"].round(1).astype(str) + "%"
        
        return df[[
            "Pitcher", "Line", 
            "Over Implied Prob", "Over Market Odds", 
            "Under Implied Prob", "Under Market Odds", "Push Prob"
        ]]

    def get_game_moneyline_odds(self):
        home_win_pct = self.player_results.get("home_win_pct", 0) / 100.0
        away_win_pct = self.player_results.get("away_win_pct", 0) / 100.0
        
        if home_win_pct == 0 and away_win_pct == 0:
            print("Warning: No win percentage data found in cache.")
            return pd.DataFrame()

        # Apply market edge to both sides.
        home_adj_prob = min(home_win_pct * (1 + self.market_edge / 2), 0.9999)
        away_adj_prob = min(away_win_pct * (1 + self.market_edge / 2), 0.9999)

        records = [
            {
                "Team": self.data["home_team"],
                "Side": "Home",
                "True Prob": home_win_pct,
                "Adj Prob": home_adj_prob
            },
            {
                "Team": self.data["away_team"],
                "Side": "Away",
                "True Prob": away_win_pct,
                "Adj Prob": away_adj_prob
            }
        ]

        df = pd.DataFrame(records)
        df = df.sort_values(by="True Prob", ascending=False).reset_index(drop=True)

        df["Fair Odds"] = df["True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Market Odds"] = df["Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Implied Prob"] = (df["True Prob"] * 100).round(1).astype(str) + "%"
        df["Market Implied Prob"] = (df["Adj Prob"] * 100).round(1).astype(str) + "%"

        return df[["Team", "Side", "Implied Prob", "Fair Odds", "Market Odds"]]

    def get_run_line_odds(self, spread=1.5):
        """
        Calculates spread/run line betting odds for any specified spread (e.g., 1.5, 2.5, 3.0) 
        based on simulation trial runs. Fully supports whole-number pushes.
        """
        home_runs = self.results.get("home_runs", [])
        away_runs = self.results.get("away_runs", [])
        
        if not home_runs or not away_runs:
            print("Warning: Run data not found in cache.")
            return pd.DataFrame()
            
        home_team = self.data["home_team"]
        away_team = self.data["away_team"]
        
        is_whole_number = (spread % 1 == 0)
        
        home_cover_count = 0
        home_push_count = 0
        home_fail_count = 0
        
        for h, a in zip(home_runs, away_runs):
            margin = h - a  # Positive means home won by X runs, negative means away won
            
            if is_whole_number:
                if margin > spread:
                    home_cover_count += 1
                elif margin == spread:
                    home_push_count += 1
                else:
                    home_fail_count += 1
            else:
                if margin > spread:
                    home_cover_count += 1
                else:
                    home_fail_count += 1
                
        home_cover_prob = home_cover_count / self.trials
        home_fail_prob = home_fail_count / self.trials
        push_prob = (home_push_count / self.trials) if is_whole_number else 0.0
        
        records = [
            {
                "Selection": f"{home_team} (-{spread})",
                "True Prob": home_cover_prob,
                "Push %": push_prob * 100
            },
            {
                "Selection": f"{away_team} (+{spread})",
                "True Prob": home_fail_prob,  # Away covers when home fails to cover the minus spread
                "Push %": push_prob * 100
            }
        ]
        
        df = pd.DataFrame(records)
        
        df["Adj Prob"] = df["True Prob"].apply(lambda p: min(p * (1 + self.market_edge), 0.9999))
        
        df["Fair Odds"] = df["True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Market Odds"] = df["Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Implied Prob"] = (df["True Prob"] * 100).round(1).astype(str) + "%"
        
        if is_whole_number:
            df["Push Prob"] = df["Push %"].round(1).astype(str) + "%"
            return df[["Selection", "Implied Prob", "Fair Odds", "Market Odds", "Push Prob"]]
        else:
            return df[["Selection", "Implied Prob", "Fair Odds", "Market Odds"]]

    # --- Report Generation Helpers ---

    def generate_props_dataframe(self, include_team_props=True):
        """
        Compiles all game, team, and player props into a structured DataFrame.
        """
        rows = []
        
        # Moneyline
        ml_df = self.get_game_moneyline_odds()
        for _, r in ml_df.iterrows():
            rows.append({"Market Type": "Moneyline", "Selection": r['Team'], "Bet": "Win", "Odds": r['Market Odds']})
                
        # Run Line
        auto_spread = self.calculate_auto_spread_line()
        rl_df = self.get_run_line_odds(auto_spread)
        for _, r in rl_df.iterrows():
            rows.append({"Market Type": "Run Line", "Selection": r['Selection'], "Bet": "Spread", "Odds": r['Market Odds']})
                
        # Game Totals
        game_metrics = [
            ("total_runs", self.results.get("total_runs", []), "Runs"),
            ("total_hr", self.results.get("total_hr", []), "HR"),
            ("total_k", self.results.get("total_k", []), "SO")
        ]
        for metric_key, stat_list, label in game_metrics:
            auto_line = self.calculate_auto_game_line(stat_list)
            df = self.get_team_game_odds(metric_key, auto_line)
            if not df.empty:
                r = df.iloc[0]
                rows.append({"Market Type": f"Game {label}", "Selection": f"O/U {auto_line}", "Bet": "Over", "Odds": r['Over Market Odds']})
                rows.append({"Market Type": f"Game {label}", "Selection": f"O/U {auto_line}", "Bet": "Under", "Odds": r['Under Market Odds']})
                
        # Team Props
        if include_team_props:
            for stat_key, label in [("hits", "Hits"), ("hr", "HR")]:
                for team_name in [self.data['away_team'], self.data['home_team']]:
                    full_key = f"away_{stat_key}" if team_name == self.data['away_team'] else f"home_{stat_key}"
                    stat_list = self.results.get(full_key, [])
                    if stat_list:
                        auto_line = self.calculate_auto_game_line(stat_list)
                        team_df = self.get_team_game_odds(stat_key, auto_line)
                        if not team_df.empty:
                            t_row = team_df[team_df['Team'] == team_name]
                            if not t_row.empty:
                                r = t_row.iloc[0]
                                rows.append({"Market Type": f"{team_name} Team {label}", "Selection": f"O/U {auto_line}", "Bet": "Over", "Odds": r['Over Market Odds']})
                                rows.append({"Market Type": f"{team_name} Team {label}", "Selection": f"O/U {auto_line}", "Bet": "Under", "Odds": r['Under Market Odds']})

        # Player Props
        player_trials = self.player_results.get("player_trials", {})
        def add_player_rows(stat_key, top_n, is_pitcher, stat_display, fixed_line=None):
            player_means = []
            for player, metrics in player_trials.items():
                stats = metrics.get(stat_key, [])
                if not stats or (is_pitcher and sum(stats) == 0): 
                    continue
                player_means.append((player, sum(stats) / self.trials, stats))
                
            for player, _, stat_list in sorted(player_means, key=lambda x: x[1], reverse=True)[:top_n]:
                line_val = fixed_line if fixed_line is not None else self.find_optimal_half_line(stat_list, self.trials)
                df = self.get_pitcher_prop_odds(stat_key, line_val) if is_pitcher else self.get_player_prop_odds(stat_key, line_val)
                target_col = "Pitcher" if is_pitcher else "Player"
                
                if not df.empty:
                    p_row = df[df[target_col] == player]
                    if not p_row.empty:
                        r = p_row.iloc[0]
                        rows.append({"Market Type": f"Player Prop ({stat_display})", "Selection": f"{player} O/U {line_val}", "Bet": "Over", "Odds": r['Over Market Odds']})
                        rows.append({"Market Type": f"Player Prop ({stat_display})", "Selection": f"{player} O/U {line_val}", "Bet": "Under", "Odds": r['Under Market Odds']})

        add_player_rows("so_pitched", 3, True, "SO Pitched")
        add_player_rows("hits_allowed", 2, True, "Hits Allowed")
        add_player_rows("h", 3, False, "Hits")
        add_player_rows("hr", 3, False, "Home Runs")
        add_player_rows("so", 3, False, "SO", fixed_line=1.5)

        return pd.DataFrame(rows)

    def generate_formatted_summary(self) -> str:
        """
        Generates a clean Markdown table summarizing core matchup game lines.
        """
        away_team = self.data['away_team']
        home_team = self.data['home_team']
        
        ml_df = self.get_game_moneyline_odds()
        away_ml = ml_df[ml_df['Team'] == away_team].iloc[0]
        home_ml = ml_df[ml_df['Team'] == home_team].iloc[0]
        
        auto_spread = self.calculate_auto_spread_line()
        rl_df = self.get_run_line_odds(auto_spread)
        away_rl = rl_df[rl_df['Selection'].str.contains(away_team)].iloc[0]
        home_rl = rl_df[rl_df['Selection'].str.contains(home_team)].iloc[0]
        
        auto_runs = self.calculate_auto_game_line(self.results.get("total_runs", []))
        auto_hr = self.calculate_auto_game_line(self.results.get("total_hr", []))
        auto_so = self.calculate_auto_game_line(self.results.get("total_k", []))

        runs_df = self.get_team_game_odds("total_runs", auto_runs).iloc[0]
        hr_df = self.get_team_game_odds("total_hr", auto_hr).iloc[0]
        so_df = self.get_team_game_odds("total_k", auto_so).iloc[0]
        
        summary_data = [
            {"Market": "Moneyline", f"{away_team}": f"{away_ml['Implied Prob']} ({away_ml['Market Odds']})", f"{home_team}": f"{home_ml['Implied Prob']} ({home_ml['Market Odds']})"},
            {"Market": "Run Line", f"{away_team}": f"{away_rl['Selection']} ({away_rl['Market Odds']})", f"{home_team}": f"{home_rl['Selection']} ({home_rl['Market Odds']})"},
            {"Market": f"Total Runs (O/U {auto_runs})", f"{away_team}": f"Over {runs_df['Over Market Odds']}", f"{home_team}": f"Under {runs_df['Under Market Odds']}"},
            {"Market": f"Total HR (O/U {auto_hr})", f"{away_team}": f"Over {hr_df['Over Market Odds']}", f"{home_team}": f"Under {hr_df['Under Market Odds']}"},
            {"Market": f"Total SO (O/U {auto_so})", f"{away_team}": f"Over {so_df['Over Market Odds']}", f"{home_team}": f"Under {so_df['Under Market Odds']}"}
        ]
        
        df_summary = pd.DataFrame(summary_data)
        return f"### Matchup Market Summary: {away_team} @ {home_team}\n\n" + df_summary.to_markdown(index=False)

class SluggerSeasonAnalyzer:
    """
    Analyzer class for processing, visualizing, and generating futures/betting lines from season simulations.
    """
    def __init__(self, pickle_filename: str = "pickles/mario_sluggers_season_cache_conditional.pkl"):
        self.pickle_filename = pickle_filename
        self.season_results = {}
        self.player_results = {}
        self.raw_totals = {}
        self.team_data = {}
        
        self.df_teams = pd.DataFrame()
        self.df_players = pd.DataFrame()
        
        # Automatically load cache and build underlying dataframes on instantiation
        self.load_cache()
        self.process_team_standings()
        self.process_player_metrics()

    def load_cache(self) -> None:
        """Load the saved SeasonSimulator payload cache from a pickle file."""
        with open(self.pickle_filename, "rb") as f:
            cache_data = pickle.load(f)
        
        self.season_results = cache_data.get("season_results", {})
        self.player_results = cache_data.get("player_results", {})
        self.raw_totals = cache_data.get("raw_player_totals", {})
        self.team_data = cache_data.get("standings_tracker", {})
        
        print("Simulation cache loaded successfully!")

    def process_team_standings(self) -> pd.DataFrame:
        """Process team-level season results into a sorted pandas DataFrame."""
        team_rows = []
        for team_name, stats in self.season_results.items():
            wins = stats.get("avg_wins", 0.0)
            losses = stats.get("avg_losses", 0.0)
            total_games = max(1, wins + losses)
            
            row = {
                "Team": team_name,
                "Avg_Wins": wins,
                "Avg_Losses": losses,
                "Win_Pct": wins / total_games,
                "RS_Per_Game": stats.get("avg_runs_scored", 0.0) / total_games,
                "RA_Per_Game": stats.get("avg_runs_allowed", 0.0) / total_games,
                "Run_Differential": (stats.get("avg_runs_scored", 0.0) - stats.get("avg_runs_allowed", 0.0)) / total_games,
                "Top_Seed_Pct": stats.get("seeding_probs", {}).get(1, 0.0),
                "Top_4_Seed_Pct": sum(stats.get("seeding_probs", {}).get(s, 0.0) for s in range(1, 5))
            }
            team_rows.append(row)
        
        self.df_teams = pd.DataFrame(team_rows).sort_values(by="Avg_Wins", ascending=False).reset_index(drop=True)
        return self.df_teams

    def process_player_metrics(self) -> pd.DataFrame:
        """Process player-level results across rosters into a comprehensive pandas DataFrame."""
        player_rows = []
        for team_name, roster_dict in self.player_results.items():
            for player_name, metrics in roster_dict.items():
                row = {
                    "Team": team_name,
                    "Player": player_name,
                    "AB": metrics.get("ab", 0.0),
                    "Hits": metrics.get("hits", 0.0),
                    "HR": metrics.get("hr", 0.0),
                    "RBI": metrics.get("rbi", 0.0),
                    "Runs": metrics.get("runs", 0.0),
                    "SO": metrics.get("so", 0.0),
                    "IP": metrics.get("ip", 0.0),
                    "H_Allowed": metrics.get("h_allowed", 0.0),
                    "R_Allowed": metrics.get("r_allowed", 0.0),
                    "SO_Pitched": metrics.get("so_pitched", 0.0),
                    "DP": metrics.get("dp", 0.0),
                    "Def_DP": metrics.get("def_dp", 0.0),
                    "TP": metrics.get("tp", 0.0),
                    "Def_TP": metrics.get("def_tp", 0.0)
                }
                
                # Calculate derived metrics safely
                ab = row["AB"]
                row["AVG"] = (row["Hits"] / ab) if ab > 0 else 0.0
                
                ip = max(0.1, row["IP"])
                row["ERA"] = row["R_Allowed"] * (9.0 / ip)
                row["WHIP"] = (row["H_Allowed"] + (row["R_Allowed"] * 0.3)) / ip
                
                player_rows.append(row)
        
        self.df_players = pd.DataFrame(player_rows)
        return self.df_players

    # --- Flexible Lookup & Summary Methods ---

    def get_players_by_stat(self, stat_key: str, n: int = 10, ascending: bool = False, custom_cols: list = None) -> pd.DataFrame:
        """
        Flexible lookup function to query players by any valid stat key.
        """
        if stat_key not in self.df_players.columns:
            raise ValueError(f"Stat key '{stat_key}' not found in player metrics. Available: {list(self.df_players.columns)}")
        
        if custom_cols is None:
            custom_cols = ["Player", "Team", "AB", "Hits", "HR", "RBI", "AVG", "ERA", "SO_Pitched"]
            custom_cols = [c for c in custom_cols if c in self.df_players.columns]
            
        return self.df_players.sort_values(by=stat_key, ascending=ascending)[custom_cols].head(n).reset_index(drop=True)

    def get_pitchers_summary(self, n: int = 10) -> pd.DataFrame:
        """Return top pitchers filtered by innings pitched and sorted by strikeouts."""
        df_pitchers = self.df_players[self.df_players["IP"] > 0].copy()
        return df_pitchers.sort_values(by="SO_Pitched", ascending=False)[["Player", "Team", "IP", "SO_Pitched", "ERA"]].head(n).reset_index(drop=True)

    def get_team_hits_summary(self) -> pd.DataFrame:
        """Summarize total expected hits per team."""
        team_hits = self.df_players.groupby("Team")["Hits"].sum().reset_index()
        team_hits.columns = ["Team", "Total Expected Hits"]
        return team_hits.sort_values(by="Total Expected Hits", ascending=False).reset_index(drop=True)

    def get_team_defense_summary(self) -> pd.DataFrame:
        """Summarize team defense metrics."""
        team_defense = self.df_players.groupby("Team")[["Def_DP", "Def_TP"]].sum().reset_index()
        return team_defense.sort_values(by="Def_DP", ascending=False).reset_index(drop=True)

    def get_standings_table(self) -> pd.DataFrame:
            """Return the sorted team standings overview table."""
            return self.df_teams[["Team", "Avg_Wins", "Avg_Losses", "Win_Pct", "RS_Per_Game", "RA_Per_Game", "Top_Seed_Pct"]]
    
    def print_league_aggregates(self) -> None:
            """Print total league-wide double plays and home runs."""
            total_dp = self.df_players["DP"].sum()
            total_league_hr = self.df_players["HR"].sum()
            print(f"Total League Double Plays: {total_dp}")
            print(f"Total Predicted Home Runs Hit League-Wide: {total_league_hr:.1f}")

    # --- Plotting Methods ---

    def plot_wins_vs_run_differential(self) -> None:
        """Plot expected season wins against average run differential."""
        plt.figure(figsize=(10, 6))
        sns.set_theme(style="whitegrid")

        sns.scatterplot(
            data=self.df_teams,
            x="Run_Differential",
            y="Avg_Wins",
            hue="Team",
            s=120,
            palette="tab10"
        )

        plt.title("Expected Season Wins vs. Run Differential (Monte Carlo Runs)", fontsize=14, fontweight="bold")
        plt.xlabel("Average Run Differential Per Game", fontsize=12)
        plt.ylabel("Projected Average Wins", fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc=2, title="Teams")
        plt.tight_layout()
        plt.show()

    def plot_rs_vs_ra(self) -> None:
        """Plot runs scored vs runs allowed per game with league-average reference lines."""
        league_avg_rs = self.df_teams["RS_Per_Game"].mean()
        league_avg_ra = self.df_teams["RA_Per_Game"].mean()

        plt.figure(figsize=(10, 6))
        sns.set_theme(style="whitegrid")

        sns.scatterplot(
            data=self.df_teams,
            x="RS_Per_Game",
            y="RA_Per_Game",
            hue="Team",
            s=140,
            palette="tab10",
            edgecolor="black"
        )

        plt.axvline(x=league_avg_rs, color="gray", linestyle="--", alpha=0.7, label=f"League Avg RS ({league_avg_rs:.2f})")
        plt.axhline(y=league_avg_ra, color="gray", linestyle="--", alpha=0.7, label=f"League Avg RA ({league_avg_ra:.2f})")

        plt.title("Predicted Runs Scored vs. Runs Allowed (Per Game)", fontsize=14, fontweight="bold")
        plt.xlabel("Average Runs Scored Per Game", fontsize=12)
        plt.ylabel("Average Runs Allowed Per Game", fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc=2, title="Teams")
        plt.tight_layout()
        plt.show()

    def plot_player_power_vs_contact(self, min_ab: float = 10.0) -> None:
        """Plot projected player Home Runs (Power) vs Batting Average (Contact) with outlier annotations."""
        df_filtered = self.df_players[self.df_players["AB"] > min_ab].copy()
        if df_filtered.empty:
            df_filtered = self.df_players.copy()

        plt.figure(figsize=(12, 7))
        sns.set_theme(style="whitegrid")

        ax = sns.scatterplot(
            data=df_filtered, x="HR", y="AVG", hue="Team", palette="tab10", edgecolor="black", alpha=0.85
        )

        # Outlier criteria based on sdev from mean
        hr_threshold = df_filtered["HR"].mean() + (1.5 * df_filtered["HR"].std())
        avg_threshold = df_filtered["AVG"].mean() + (1.5 * df_filtered["AVG"].std())

        hr_comb_threshold = df_filtered["HR"].mean() + (1.25 * df_filtered["HR"].std())
        avg_comb_threshold = df_filtered["AVG"].mean() + (1.25 * df_filtered["AVG"].std())

        neg_avg_threshold = df_filtered["AVG"].mean() - (1.4 * df_filtered["AVG"].std())

        outliers = df_filtered[
            (df_filtered["HR"] >= hr_threshold) | 
            (df_filtered["AVG"] >= avg_threshold) | 
            ((df_filtered["HR"] >= hr_comb_threshold) & (df_filtered["AVG"] >= avg_comb_threshold))
        ]
        
        for _, row in outliers.iterrows():
            ax.annotate(
                row["Player"], 
                (row["HR"], row["AVG"]),
                xytext=(8, 4), textcoords="offset points",
                fontsize=9, fontweight="bold", color="green",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.7),
                arrowprops=dict(arrowstyle="-", color="gray", lw=0.8, alpha=0.6)
            )

        outliers_neg = df_filtered[df_filtered["AVG"] <= neg_avg_threshold]
        for _, row in outliers_neg.iterrows():
            ax.annotate(
                row["Player"], 
                (row["HR"], row["AVG"]),
                xytext=(8, 4), textcoords="offset points",
                fontsize=9, fontweight="bold", color="red",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.7),
                arrowprops=dict(arrowstyle="-", color="gray", lw=0.8, alpha=0.6)
            )

        plt.title("Preseason Player Projections: Power (HR) and Contact (AVG)", fontsize=14, fontweight="bold")
        plt.xlabel("Projected Home Runs", fontsize=12)
        plt.ylabel("Projected Batting Average", fontsize=12)

        plt.legend(bbox_to_anchor=(1.02, 1), loc=2, borderaxespad=0, title="Teams & Scale")
        plt.tight_layout()
        plt.show()

    def plot_playoff_seeding_heatmap(self) -> None:
        """Plot a heatmap of playoff seeding probabilities for each team."""
        matrix_data = []
        num_teams = len(self.season_results)
        
        for team, stats in self.season_results.items():
            row = {"Team": team}
            seeding_probs = stats.get("seeding_probs", {})
            for seed in range(1, num_teams + 1):
                row[f"Seed {seed}"] = seeding_probs.get(seed, 0.0)
            matrix_data.append(row)

        if not matrix_data:
            print("No season results available for seeding heatmap.")
            return

        df_matrix = pd.DataFrame(matrix_data).set_index("Team")

        plt.figure(figsize=(12, 6))
        sns.set_theme(style="whitegrid")
        sns.heatmap(df_matrix, annot=True, fmt=".1f", cmap="Blues", cbar=True, linewidths=.5)

        plt.title("Playoff Seeding Heatmap", fontsize=14, fontweight="bold")
        plt.xlabel("Seed", fontsize=12)
        plt.ylabel("Team", fontsize=12)
        plt.tight_layout()
        plt.show()

    # --- Betting Odds & Futures Helpers ---

    def calculate_futures_odds(self, stat_key: str, entity_name: str = "Player", market_edge: float = 0.05, top_n: int = 15) -> pd.DataFrame:
        """
        Simulates crown/award winners across all Monte Carlo run lists stored in `raw_totals` 
        and calculates sportsbook futures odds.
        """
        crown_winners = []
        num_runs = 0
        for _, roster_dict in self.raw_totals.items():
            for _, metrics in roster_dict.items():
                val_list = metrics.get(stat_key, [])
                if val_list:
                    num_runs = len(val_list)
                    break
            if num_runs > 0:
                break

        if num_runs == 0:
            raise ValueError(f"No simulation run lists found in raw_totals for stat key: {stat_key}")

        for run_idx in range(num_runs):
            max_val = -1
            winner = None
            
            for team_name, roster_dict in self.raw_totals.items():
                for player_name, metrics in roster_dict.items():
                    val_list = metrics.get(stat_key, [])
                    if run_idx < len(val_list):
                        val = val_list[run_idx]
                        if val > max_val:
                            max_val = val
                            winner = player_name
                            
            if winner:
                crown_winners.append(winner)

        counts = dict(Counter(crown_winners))
        
        # Convert dictionary to DataFrame for odds formatting
        df = pd.DataFrame(list(counts.items()), columns=[entity_name, "Score"])
        total_score = df["Score"].sum()
        df["True Prob"] = df["Score"] / total_score if total_score > 0 else 0.0
        df["Adjusted Prob"] = df["True Prob"] * (1 + market_edge)

        df = df.sort_values(by="True Prob", ascending=False).reset_index(drop=True)
            
        raw_fair_odds = df["True Prob"].apply(prob_to_odds)
        raw_market_odds = df["Adjusted Prob"].apply(prob_to_odds)

        df["Fair Odds"] = raw_fair_odds.apply(round_odds).apply(format_odds_string)
        df["Adjusted Market Odds"] = raw_market_odds.apply(round_odds).apply(format_odds_string)

        df["Fair Implied Prob"] = (df["True Prob"] * 100).round(1).astype(str) + "%"
        df["Market Implied Prob"] = (df["Adjusted Prob"] * 100).round(1).astype(str) + "%"
        
        return df[[entity_name, "Fair Implied Prob", "Fair Odds", "Market Implied Prob", "Adjusted Market Odds"]].head(top_n)

    def get_independent_threshold_odds(self, stat_key: str, min_count, entity_name: str = "Player", market_edge: float = 0.05) -> pd.DataFrame:
        """Calculates independent Over/Under threshold probabilities and betting odds for players."""
        records = []
        total_runs = 0
        
        for _, roster_dict in self.raw_totals.items():
            for _, metrics in roster_dict.items():
                stat_list = metrics.get(stat_key, [])
                if stat_list:
                    total_runs = len(stat_list)
                    break
            if total_runs > 0:
                break

        if total_runs == 0:
            raise ValueError(f"No simulation data found for stat key: {stat_key}")

        for team_name, roster_dict in self.raw_totals.items():
            for player_name, metrics in roster_dict.items():
                stat_list = metrics.get(stat_key, [])
                if not stat_list:
                    continue
                    
                successes = sum(1 for val in stat_list if val >= min_count)
                over_raw_prob = successes / total_runs
                under_raw_prob = 1.0 - over_raw_prob
                
                over_adj_prob = min(over_raw_prob * (1 + market_edge), 0.9999)
                under_adj_prob = min(under_raw_prob * (1 + market_edge), 0.9999)
                
                records.append({
                    entity_name: player_name,
                    "Team": team_name,
                    "Line": f"O/U {min_count}",
                    "Over True Prob": over_raw_prob,
                    "Over Adj Prob": over_adj_prob,
                    "Under True Prob": under_raw_prob,
                    "Under Adj Prob": under_adj_prob
                })

        df = pd.DataFrame(records)
        if df.empty:
            return df

        df = df.sort_values(by="Over True Prob", ascending=False).reset_index(drop=True)
        
        df["Over Fair Odds"] = df["Over True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Over Market Odds"] = df["Over Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Over Implied Prob"] = (df["Over True Prob"] * 100).round(1).astype(str) + "%"

        df["Under Fair Odds"] = df["Under True Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Under Market Odds"] = df["Under Adj Prob"].apply(prob_to_odds).apply(round_odds).apply(format_odds_string)
        df["Under Implied Prob"] = (df["Under True Prob"] * 100).round(1).astype(str) + "%"
        
        return df[[entity_name, "Team", "Line", "Over Implied Prob", "Over Market Odds", "Under Implied Prob", "Under Market Odds"]]
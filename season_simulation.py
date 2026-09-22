import statistics
import pickle
import os
import random
from models.team import Team
from models.simulation import MonteCarloSimulation
from data.league_stats import STADIUM_MODIFIERS
import pandas as pd
from tqdm import tqdm
import re

class SeasonSimulator:
    def __init__(self, teams_dict, schedule_list):
        self.teams_dict = teams_dict
        self.canonical_teams = sorted(list(teams_dict.keys()))
        self.schedule_list = schedule_list
        self.season_results = None
        self.player_results = None
        self.player_season_totals = None
        self.standings_tracker = None

    def _resolve_ties_and_determine_seeds(self, sorted_standings, current_wins, current_rs, current_ra, monte_carlo_trials=100):
        stadium_choices = list(STADIUM_MODIFIERS.keys())
        wins_groups = {}
        for team in sorted_standings:
            w = current_wins[team]
            if w not in wins_groups:
                wins_groups[w] = []
            wins_groups[w].append(team)

        resolved_order = []
        
        for w in sorted(wins_groups.keys(), reverse=True):
            group = wins_groups[w]
            if len(group) == 1:
                resolved_order.append(group[0])
            else:
                if len(group) == 2:
                    team_high, team_low = group[0], group[1]
                    chosen_stadium = random.choice(stadium_choices)
                    sim = MonteCarloSimulation(team_home=self.teams_dict[team_high], team_away=self.teams_dict[team_low], stadium_name=chosen_stadium)
                    res = sim.run(trials=monte_carlo_trials)
                    
                    if random.random() < (res["home_win_pct"] / 100.0):
                        resolved_order.extend([team_high, team_low])
                    else:
                        resolved_order.extend([team_low, team_high])
                else:
                    current_pool = list(group)
                    group_ranking = []
                    
                    while len(current_pool) > 1:
                        team_low = current_pool.pop() 
                        team_high = current_pool.pop()
                        
                        chosen_stadium = random.choice(stadium_choices)
                        sim = MonteCarloSimulation(team_home=self.teams_dict[team_high], team_away=self.teams_dict[team_low], stadium_name=chosen_stadium)
                        res = sim.run(trials=monte_carlo_trials)
                        
                        if random.random() < (res["home_win_pct"] / 100.0):
                            winner = team_high
                            loser = team_low
                        else:
                            winner = team_low
                            loser = team_high
                        
                        group_ranking.insert(0, loser)
                        current_pool.append(winner)
                        current_pool.sort(key=lambda t: (current_rs[t] - current_ra[t]), reverse=True)
                    
                    group_ranking.insert(0, current_pool[0])
                    resolved_order.extend(group_ranking)
                    
        return resolved_order

    def simulate_season(self, monte_carlo_trials=100, season_monte_carlo_runs=10, 
                        actual_wins=None, actual_losses=None, actual_rs=None, 
                        actual_ra=None, actual_player_stats=None):
        
        actual_wins = actual_wins or {t: 0 for t in self.canonical_teams}
        actual_losses = actual_losses or {t: 0 for t in self.canonical_teams}
        actual_rs = actual_rs or {t: 0 for t in self.canonical_teams}
        actual_ra = actual_ra or {t: 0 for t in self.canonical_teams}
        actual_player_stats = actual_player_stats or {}

        standings_tracker = {team: {"wins": [], "losses": [], "runs_scored": [], "runs_allowed": [], "team_hr": [], "ranks": []} for team in self.canonical_teams}
        seed_count = {team: {i: 0 for i in range(1, len(self.canonical_teams) + 1)} for team in self.canonical_teams}
        
        player_season_totals = {team: {} for team in self.canonical_teams}
        for team, t_obj in self.teams_dict.items():
            for p in t_obj.lineup:
                base_p = actual_player_stats.get(team, {}).get(p.name, {})
                player_season_totals[team][p.name] = {
                    "ab": [], "hits": [], "hr": [], "rbi": [], "runs": [], "so": [],
                    "ip": [], "h_allowed": [], "r_allowed": [], "so_pitched": [], 
                    "dp": [], "tp": [], "def_dp": [], "def_tp": []
                }

        run_iter = tqdm(range(season_monte_carlo_runs), desc="Simulating Seasons", unit="season")
        for _ in run_iter:
            current_wins = actual_wins.copy()
            current_losses = actual_losses.copy()
            current_rs = actual_rs.copy()
            current_ra = actual_ra.copy()

            current_player_stats = {}
            for team, t_obj in self.teams_dict.items():
                current_player_stats[team] = {}
                team_actuals = actual_player_stats.get(team, {})
                for p in t_obj.roster:
                    bp = team_actuals.get(p.name, {})
                    current_player_stats[team][p.name] = {
                        "ab": bp.get("AB", 0.0),
                        "hits": bp.get("H", 0.0),
                        "hr": bp.get("HR", 0.0),
                        "rbi": bp.get("RBI", 0.0),
                        "runs": bp.get("R", 0.0),
                        "so": bp.get("SO", 0.0),
                        "ip": bp.get("IP", 0.0),
                        "h_allowed": bp.get("H_allowed", 0.0),
                        "r_allowed": bp.get("R_allowed", 0.0),
                        "so_pitched": bp.get("SO_allowed", 0.0), # mapping standard sheet structure
                        "dp": bp.get("DP Into", 0.0),
                        "tp": bp.get("TP Into", 0.0),
                        "def_dp": 0.0,
                        "def_tp": 0.0,
                    }

            for game in self.schedule_list:
                if game.get("completed", False):
                    continue

                home_team = game["home"]
                away_team = game["away"]
                chosen_stadium = game["stadium"]

                if home_team not in self.teams_dict or away_team not in self.teams_dict:
                    continue
                
                h_team_obj = self.teams_dict[home_team]
                a_team_obj = self.teams_dict[away_team]

                sim = MonteCarloSimulation(team_home=h_team_obj, team_away=a_team_obj, stadium_name=chosen_stadium)
                game_res = sim.run(trials=monte_carlo_trials)

                h_win_prob = game_res["home_win_pct"] / 100.0
                home_scored = game_res["home_avg_runs"]
                away_scored = game_res["away_avg_runs"]

                current_rs[home_team] += home_scored
                current_ra[home_team] += away_scored
                current_rs[away_team] += away_scored
                current_ra[away_team] += home_scored

                p_avgs = game_res["player_averages"]
                for team_name, t_obj in [(home_team, h_team_obj), (away_team, a_team_obj)]:
                    c_stats = current_player_stats[team_name]
                    for p in t_obj.roster:
                        p_metrics = p_avgs.get(p.name)
                        if not p_metrics:
                            continue
                        
                        c_stats[p.name]["ab"] += p_metrics.get("avg_AB", 0.0)
                        c_stats[p.name]["hits"] += p_metrics.get("avg_H", 0.0)
                        c_stats[p.name]["hr"] += p_metrics.get("avg_HR", 0.0)
                        c_stats[p.name]["rbi"] += p_metrics.get("avg_RBI", 0.0)
                        c_stats[p.name]["runs"] += p_metrics.get("avg_R", 0.0)
                        c_stats[p.name]["so"] += p_metrics.get("avg_SO", 0.0)
                        c_stats[p.name]["ip"] += p_metrics.get("avg_IP", 0.0)
                        c_stats[p.name]["h_allowed"] += p_metrics.get("avg_H_allowed", 0.0)
                        c_stats[p.name]["r_allowed"] += p_metrics.get("avg_R_allowed", 0.0)
                        c_stats[p.name]["so_pitched"] += p_metrics.get("avg_SO_pitched", 0.0)
                        c_stats[p.name]["dp"] += p_metrics.get("avg_DP", 0.0)
                        c_stats[p.name]["tp"] += p_metrics.get("avg_TP", 0.0)
                        c_stats[p.name]["def_dp"] += p_metrics.get("avg_def_DP", 0.0)
                        c_stats[p.name]["def_tp"] += p_metrics.get("avg_def_TP", 0.0)

                if random.random() < h_win_prob:
                    current_wins[home_team] += 1
                    current_losses[away_team] += 1
                else:
                    current_wins[away_team] += 1
                    current_losses[home_team] += 1

            # Log this run's final player totals
            for team_name in self.canonical_teams:
                for p_name, metrics in current_player_stats[team_name].items():
                    for k, val in metrics.items():
                        player_season_totals[team_name][p_name][k].append(val)

            preliminary_sorted_standings = sorted(
                self.canonical_teams,
                key=lambda t: (current_wins[t], (current_rs[t] - current_ra[t])),
                reverse=True
            )
            sorted_standings = self._resolve_ties_and_determine_seeds(
                preliminary_sorted_standings, current_wins, current_rs, current_ra, monte_carlo_trials=monte_carlo_trials
            )

            current_team_hrs = {}
            for team_name in self.canonical_teams:
                total_hr = sum(metrics["hr"] for p_name, metrics in current_player_stats[team_name].items())
                current_team_hrs[team_name] = total_hr

            for rank_idx, team in enumerate(sorted_standings, start=1):
                seed_count[team][rank_idx] += 1
                standings_tracker[team]["wins"].append(current_wins[team])
                standings_tracker[team]["losses"].append(current_losses[team])
                standings_tracker[team]["runs_scored"].append(current_rs[team])
                standings_tracker[team]["runs_allowed"].append(current_ra[team])
                standings_tracker[team]["team_hr"].append(current_team_hrs[team])
                standings_tracker[team]["ranks"].append(rank_idx)

        # Compile final aggregated team data
        final_summary = {}
        for team in self.canonical_teams:
            t_runs = standings_tracker[team]["runs_scored"]
            t_allowed = standings_tracker[team]["runs_allowed"]
            final_summary[team] = {
                "avg_wins": statistics.mean(standings_tracker[team]["wins"]),
                "avg_losses": statistics.mean(standings_tracker[team]["losses"]),
                "avg_runs_scored": statistics.mean(t_runs),
                "avg_runs_allowed": statistics.mean(t_allowed),
                "avg_team_hr": statistics.mean(standings_tracker[team]["team_hr"]),
                "seeding_probs": {seed: (count / season_monte_carlo_runs) * 100 for seed, count in seed_count[team].items()}
            }

        # Compile final aggregated player data (averages per season across MC runs)
        final_player_summary = {}
        for team in self.canonical_teams:
            final_player_summary[team] = {}
            for p_name, metrics in player_season_totals[team].items():
                final_player_summary[team][p_name] = {
                    k: statistics.mean(v) if v else 0.0 for k, v in metrics.items()
                }

        self.season_results = final_summary
        self.player_results = final_player_summary
        self.player_season_totals = player_season_totals
        self.standings_tracker = standings_tracker
        return final_summary

    def print_team_player_stats(self, team_name):
        if not self.player_results:
            print("No player results available. Run simulate_season() first.")
            return
        
        if team_name not in self.player_results:
            print(f"Team '{team_name}' not found in results.")
            return

        t_obj = self.teams_dict[team_name]
        p_data = self.player_results[team_name]

        print("\n" + "=" * 105)
        print(f"PLAYER SEASON PROJECTIONS — {team_name.upper()}")
        print("=" * 105)
        print("BATTING STATS")
        print(f"{'Player Name':<20} | {'AB':<6} | {'H':<6} | {'HR':<6} | {'RBI':<6} | {'R':<6} | {'SO':<6} | {'AVG':<6}")
        print("-" * 105)

        for p in t_obj.lineup:
            stats = p_data[p.name]
            ab = stats["ab"]
            hits = stats["hits"]
            avg = (hits / ab) if ab > 0 else 0.0
            print(f"{p.name:<20} | {ab:<6.1f} | {hits:<6.1f} | {stats['hr']:<6.1f} | {stats['rbi']:<6.1f} | {stats['runs']:<6.1f} | {stats['so']:<6.1f} | {avg:<6.3f}")

        print("\n" + "PITCHING STATS")
        print(f"{'Pitcher Name':<20} | {'IP':<6} | {'H Allowed':<10} | {'R Allowed':<10} | {'SO Pitched':<12} | {'ERA':<8} | {'WHIP':<8}")
        print("-" * 105)

        for p in t_obj.pitching_order:
            stats = p_data[p.name]
            ip = max(0.1, stats["ip"])
            er = stats["r_allowed"] * (9.0 / ip) 
            whip = (stats["h_allowed"] + (stats["r_allowed"] * 0.3)) / ip
            print(f"{p.name:<20} | {ip:<6.1f} | {stats['h_allowed']:<10.1f} | {stats['r_allowed']:<10.1f} | {stats['so_pitched']:<12.1f} | {er:<8.2f} | {whip:<8.2f}")
        print("=" * 105)

    def save_to_pickle(self, filename="season_simulation_cache.pkl"):
        if not self.season_results:
            raise ValueError("Run simulate_season() before attempting to cache results.")
        payload = {"season_results": self.season_results, "player_results": self.player_results, "raw_player_totals": self.player_season_totals, "standings_tracker": self.standings_tracker}
        with open(filename, "wb") as f:
            pickle.dump(payload, f)
        print(f"Season simulation data successfully saved to {filename}")

    def print_season_standings(self):
        if not self.season_results:
            print("No season results available. Run simulate_season() first.")
            return

        print("=" * 110)
        print(f"FINAL SEASON & SEEDING PROJECTIONS")
        print("=" * 110)
        print(f"{'Team Name':<30} | {'W-L':<10} | {'RS/G':<6} | {'RA/G':<6} | {'1 Seed %':<12} | {'Top 4 Seed %':<16}")
        print("-" * 110)

        sorted_teams = sorted(self.season_results.keys(), key=lambda x: self.season_results[x]["avg_wins"], reverse=True)
        
        for team in sorted_teams:
            stats = self.season_results[team]
            wl_str = f"{stats['avg_wins']:.1f}-{stats['avg_losses']:.1f}"
            rs_g = stats['avg_runs_scored'] / max(1, (stats['avg_wins'] + stats['avg_losses']))
            ra_g = stats['avg_runs_allowed'] / max(1, (stats['avg_wins'] + stats['avg_losses']))
            top_seed_pct = stats['seeding_probs'].get(1, 0.0)
            top_4_pct = sum(stats['seeding_probs'].get(s, 0.0) for s in range(1, 5))

            print(f"{team:<30} | {wl_str:<10} | {rs_g:<6.2f} | {ra_g:<6.2f} | {top_seed_pct:<12.1f}% | {top_4_pct:<16.1f}%")
        print("=" * 105)

# --- Data Parsing & Initialization Helpers ---

blues_pitchers = ["Peach", "Luigi", "Rainer"]
custoadians_pitchers = ["Donkey Kong", "Toadsworth", "Curtis S"]
fighters_pitchers = ["Bowser", "Jinu Kim", "Blue Magikoopa"]
top1_pitchers = ['Wario', 'Ronald R', 'Yellow Magikoopa']
gasters_pitchers = ['Baby Peach', 'Ass Helm', 'Rocky V']
wht_pitchers = ['Birdo', 'Blooper', 'Flowery']
emails_pitchers = ['Mario', 'Red Magikoopa', 'Hunter B']
actions_pitchers = ['Funky Kong', 'Boo', 'Tony Zaret', 'Action 52']
koopas_pitchers = ['Shredder', 'Bowser Jr.', 'Goomba', 'ChrisPratt']
miis_pitchers = ['Waluigi', 'Vector', 'Wiggler', 'Baby Daisy']

def generate_team_raw(file_path):
    team_names = [
        "Cheetahmen Actions", "Goodraian Gasters", "Water Blues", 
        "Deep State Deleted Emails", "Sassy Freedom Fighters", 
        "The Top 1%", "Teenage Mutant Ninja Koopas", 
        "The Worlds Hardest Team", "Despicable Miis", "Evil Custoadians"
    ]

    team_order_map = {
        "Cheetahmen Actions":           ["Yoshi", "Action 52", "Toad", "Blue Pianta", "Light Blue Yoshi", "Tony Zaret", "Funky Kong", "Boo", "Blue Noki"],
        "Goodraian Gasters":            ["Yellow Yoshi", "Ass Helm", "Yellow Toad", "Daisy", "Blue Toad", "Baby Peach", "Red Pianta", "Rocky V", "Red Noki"],
        "Water Blues":                  ["Green Toad", "The Sailor", "Luigi", "King K. Rool", "Red Kritter", "Rainer", "Fire Bro", "Dixie Kong", "Peach"],
        "Deep State Deleted Emails":    ["Mario", "Red Koopa", "Dark Bones", "Green Kritter", "Hunter B", "Red Shy Guy", "Hillary C", "Red Magikoopa", "Red Yoshi"],
        "Sassy Freedom Fighters":       ["Boomerang Bro", "Mudae Bot", "Blue Kritter", "Bowser", "Green Paratroopa", "Red Paratroopa", "Jinu Kim", "Paragoomba", "Blue Magikoopa"],
        "The Top 1%":                   ["Monty Mole", "Yellow Magikoopa", "Ronald R", "Wario", "Blue Shy Guy", "Margaret T", "Blue Dry Bones", "Tiny Kong", "Gray Shy Guy"],
        "Teenage Mutant Ninja Koopas":  ["Green Koopa", "Green Dry Bones", "ChrisPratt", "Hammer Bro", "Green Shy Guy", "Shredder", "Bowser Jr.", "Green Magikoopa", "Green Paratroopa"],
        "The Worlds Hardest Team":      ["Baby Luigi", "Baby Mario", "Blooper", "Petey Piranha", "Flowery", "Green Noki", "Birdo", "Dashie", "Toadette"], 
        "Despicable Miis":              ["Waluigi", "Wiggler", "Kyle", "Yellow Pianta", "Baby Daisy", "Vector", "Brown Kritter", "Yellow Shy Guy", "Diddy Kong"],
        "Evil Custoadians":             ["Pink Yoshi", "Baby DK", "Donkey Kong", "Purple Toad", "Toadsworth", "Curtis S", "King Boo", "Jungkook", "Gray Dry Bones"]
    }

    staminas = {
        "Peach": 60, "Luigi": 45, "Rainer": 45, "The Sailor": 45, "Donkey Kong": 50, 
        "Toadsworth": 45, "Curtis S": 45, "Jinu Kim": 50, "Bowser": 50, "Blue Magikoopa": 30, 
        "Yellow Magikoopa": 30, "Ronald R": 45, "Wario": 70, "Ass Helm": 50, "Baby Peach": 30, 
        "Rocky V": 45, "Blooper": 45, "Flowery": 45, "Birdo": 66, "Mario": 58, 
        "Hunter B": 45, "Red Magikoopa": 30, "Action 52": 45, "Tony Zaret": 60, "Boo": 44, 
        "ChrisPratt": 45, "Shredder": 48, "Bowser Jr.": 45, "Goomba": 40, "Waluigi": 50, 
        "Wiggler": 45, "Baby Daisy": 30, "Vector": 25,  "Funky Kong": 60,
    }

    all_teams_data = {}

    def safe_int(val):
        if pd.isna(val):
            return 0
        return int(val)

    for team in team_names:
        df = pd.read_excel(file_path, sheet_name=team, header=0)
        player_rows = df.iloc[0:9]

        team_list = []
        for _, row in player_rows.iterrows():
            player_data = {
                "name": row["Player"],
                "PA": safe_int(row["Plate Appearances"]),
                "AB": safe_int(row["At-Bats"]),
                "H": safe_int(row["Hits"]),
                "SO": safe_int(row.iloc[9]),
                "DP Into": safe_int(row["DP Into"]),
                "TP Into": 0, 
                "1B": safe_int(row["Singles"]),
                "2B": safe_int(row["Doubles"]),
                "3B": safe_int(row["Triples"]),
                "HR": safe_int(row["Home Runs"]),
                "BF": safe_int(row["Batters Faced"]),
                "H_allowed": safe_int(row["Hits Allowed"]),
                "SO_allowed": safe_int(row.iloc[19]),
                "HR_allowed": safe_int(row["HR Allowed"]),
                "Stamina": staminas.get(row["Player"], 50),
                "DP": row.get("DP", 0),
                "TP": row.get("TP", 0),
            }
            team_list.append(player_data)

        if team in team_order_map:
            desired_order = team_order_map[team]
            team_list = sorted(team_list, key=lambda x: desired_order.index(x["name"]) if x["name"] in desired_order else 999)
        
        all_teams_data[team] = team_list

    return all_teams_data

def load_teams_data(preseason_path='stats.xlsx', season_path=None, use_season_stats=False):
    preseason_data = generate_team_raw(preseason_path)
    if not use_season_stats or not season_path or not os.path.exists(season_path):
        print("Initializing teams using preseason stats only.")
        return preseason_data
    
    print(f"Blending/Loading stats from {season_path} alongside preseason baseline.")
    season_data = generate_team_raw(season_path)
    blended_data = {}
    for team_name, preseason_roster in preseason_data.items():
        season_roster = {p["name"]: p for p in season_data.get(team_name, [])}
        blended_roster = []
        
        for p_pre in preseason_roster:
            p_name = p_pre["name"]
            if p_name in season_roster:
                p_seas = season_roster[p_name]
                blended_player = p_pre.copy()
                for key in ["PA", "AB", "H", "SO", "DP Into", "TP Into", "1B", "2B", "3B", "HR", "BF", "H_allowed", "SO_allowed", "HR_allowed", "DP", "TP"]:
                    blended_player[key] = p_pre.get(key, 0) + p_seas.get(key, 0)
                blended_roster.append(blended_player)
            else:
                blended_roster.append(p_pre)
                
        blended_data[team_name] = blended_roster
        
    return blended_data

def parse_game_outcome(win_status, score, home_short, name_mapping):
    if not isinstance(win_status, str) or not win_status.strip():
        return False, None, None, None

    status_str = win_status.strip()
    if "Win" in status_str or "Wins" in status_str:
        winner_short = status_str.replace("Win", "").replace("Wins", "").strip()
        winner = name_mapping.get(winner_short, winner_short)
        
        h_score, a_score = None, None
        if isinstance(score, str):
            score_match = re.search(r'(\d+)-(\d+)', score)
            if score_match:
                s1, s2 = int(score_match.group(1)), int(score_match.group(2))
                home_team = name_mapping.get(home_short, home_short)
                if winner == home_team:
                    h_score, a_score = max(s1, s2), min(s1, s2)
                else:
                    h_score, a_score = min(s1, s2), max(s1, s2)
                    
        return True, h_score, a_score, True
        
    return False, None, None, False

def load_schedule_and_actuals(file_path):
    df_schedule = pd.read_excel(file_path, sheet_name="Match Schedule", header=0)
    
    name_mapping = {
        "Actions": "Cheetahmen Actions", "Gasters": "Goodraian Gasters",
        "Blues": "Water Blues", "Emails": "Deep State Deleted Emails",
        "Fighters": "Sassy Freedom Fighters", "Top 1%": "The Top 1%",
        "Koopas": "Teenage Mutant Ninja Koopas", "Team": "The Worlds Hardest Team",
        "Miis": "Despicable Miis", "Custoadians": "Evil Custoadians"
    }
    
    schedule_list = []
    canonical_teams = list(name_mapping.values())
    actual_wins = {t: 0 for t in canonical_teams}
    actual_losses = {t: 0 for t in canonical_teams}
    actual_rs = {t: 0 for t in canonical_teams}
    actual_ra = {t: 0 for t in canonical_teams}
    
    for _, row in df_schedule.iterrows():
        raw_home = row.iloc[1]
        raw_away = row.iloc[3]
        stadium = row.iloc[4]
        win_status = row.iloc[5]
        score = row.iloc[6] if len(row) > 6 else None
        
        if pd.notna(raw_home) and pd.notna(raw_away) and pd.notna(stadium):
            home_short = str(raw_home).strip()
            away_short = str(raw_away).strip()
            
            home_team = name_mapping.get(home_short, home_short)
            away_team = name_mapping.get(away_short, away_short)
            
            is_completed, h_score, a_score, completed_flag = parse_game_outcome(
                win_status, score, home_short, name_mapping
            )
            
            schedule_list.append({
                "home": home_team, 
                "away": away_team, 
                "stadium": str(stadium).strip(), 
                "completed": completed_flag
            })
            
            if is_completed and h_score is not None and a_score is not None:
                actual_rs[home_team] += h_score
                actual_ra[home_team] += a_score
                actual_rs[away_team] += a_score
                actual_ra[away_team] += h_score
                
                if h_score > a_score:
                    actual_wins[home_team] += 1
                    actual_losses[away_team] += 1
                else:
                    actual_wins[away_team] += 1
                    actual_losses[home_team] += 1
                    
    return schedule_list, actual_wins, actual_losses, actual_rs, actual_ra

def load_actual_player_stats(file_path, team_names):
    actual_player_stats = {}
    if not os.path.exists(file_path):
        return actual_player_stats

    def parse_ip(val):
        if pd.isna(val):
            return 0.0
        try:
            ip_float = float(val)
            whole_innings = int(ip_float)
            outs = round((ip_float - whole_innings) * 10)
            return float(whole_innings) + (outs / 3.0)
        except (ValueError, TypeError):
            return 0.0
        
    for team in team_names:
        try:
            df = pd.read_excel(file_path, sheet_name=team, header=0)
            actual_player_stats[team] = {}
            for _, row in df.iterrows():
                raw_ip = row.get("Innings Pitched", row.get("IP", 0.0))
                starting_ip = parse_ip(raw_ip)
                p_name = row.get("Player")
                if pd.isna(p_name):
                    continue
                actual_player_stats[team][p_name] = {
                    "AB": row.get("At-Bats", 0),
                    "H": row.get("Hits", 0),
                    "HR": row.get("Home Runs", 0),
                    "RBI": row.get("RBIs", 0),
                    "R": row.get("Runs", 0),
                    "SO": row.iloc[9] if len(row) > 9 else 0,
                    "IP": starting_ip,
                    "H_allowed": row.get("Hits Allowed", 0),
                    "R_allowed": row.get("Runs Allowed", 0),
                    "SO_allowed": row.iloc[19] if len(row) > 19 else 0,
                    "DP Into": row.get("DP Into", 0),
                    "TP Into": row.get("TP Into", 0),
                    "DP": row.get("DP", 0),
                    "TP": row.get("TP", 0),
                }
        except Exception as e:
            print(f"Could not load player stats for {team} from {file_path}: {e}")
            
    return actual_player_stats

if __name__ == "__main__":
    USE_SEASON_STATS = True
    PRESEASON_FILE = 'data/preseason-stats.xlsx'
    SEASON_FILE = 'data/season-stats.xlsx'

    team_names = [
        "Cheetahmen Actions", "Goodraian Gasters", "Water Blues", 
        "Deep State Deleted Emails", "Sassy Freedom Fighters", 
        "The Top 1%", "Teenage Mutant Ninja Koopas", 
        "The Worlds Hardest Team", "Despicable Miis", "Evil Custoadians"
    ]

    data = load_teams_data(
        preseason_path=PRESEASON_FILE, 
        season_path=SEASON_FILE, 
        use_season_stats=USE_SEASON_STATS
    )

    teams_map = {
        "Water Blues": Team("Water Blues", data["Water Blues"], blues_pitchers),
        "Evil Custoadians": Team("Evil Custoadians", data["Evil Custoadians"], custoadians_pitchers),
        "Sassy Freedom Fighters": Team("Sassy Freedom Fighters", data["Sassy Freedom Fighters"], fighters_pitchers),
        "The Top 1%": Team("The Top 1%", data["The Top 1%"], top1_pitchers),
        "Goodraian Gasters": Team("Goodraian Gasters", data["Goodraian Gasters"], gasters_pitchers),
        "The Worlds Hardest Team": Team("The Worlds Hardest Team", data["The Worlds Hardest Team"], wht_pitchers),
        "Despicable Miis": Team("Despicable Miis", data["Despicable Miis"], miis_pitchers),
        "Teenage Mutant Ninja Koopas": Team("Teenage Mutant Ninja Koopas", data["Teenage Mutant Ninja Koopas"], koopas_pitchers),
        "Cheetahmen Actions": Team("Cheetahmen Actions", data["Cheetahmen Actions"], actions_pitchers),
        "Deep State Deleted Emails": Team("Deep State Deleted Emails", data["Deep State Deleted Emails"], emails_pitchers)
    }

    if USE_SEASON_STATS and os.path.exists(SEASON_FILE):
        print(f"Loading schedule and actuals from {SEASON_FILE}")
        schedule, act_wins, act_losses, act_rs, act_ra = load_schedule_and_actuals(SEASON_FILE)
        act_player_stats = load_actual_player_stats(SEASON_FILE, team_names)
    else:
        print(f"Loading schedule from {PRESEASON_FILE} (Preseason mode)")
        schedule, act_wins, act_losses, act_rs, act_ra = load_schedule_and_actuals(PRESEASON_FILE)
        act_player_stats = {t: {} for t in team_names}
        act_wins = {t: 0 for t in team_names}
        act_losses = {t: 0 for t in team_names}
        act_rs = {t: 0 for t in team_names}
        act_ra = {t: 0 for t in team_names}

    season_sim = SeasonSimulator(teams_dict=teams_map, schedule_list=schedule)
    season_results = season_sim.simulate_season(
        monte_carlo_trials=1, 
        season_monte_carlo_runs=10000,
        actual_wins=act_wins,
        actual_losses=act_losses,
        actual_rs=act_rs,
        actual_ra=act_ra,
        actual_player_stats=act_player_stats
    )
    
    season_sim.print_season_standings()
    season_sim.print_team_player_stats("Cheetahmen Actions")
    season_sim.save_to_pickle("pickles/mario_sluggers_season_cache_conditional.pkl")
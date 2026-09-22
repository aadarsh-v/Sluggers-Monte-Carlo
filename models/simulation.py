import statistics
import pickle
import os
from models.game import GameEngine
from data.league_stats import STADIUM_MODIFIERS

class MonteCarloSimulation:
    def __init__(self, team_home, team_away, stadium_name="Mario_Stadium", save_cache=False, cache_filename="sim_cache.pkl"):
        self.home_team = team_home
        self.away_team = team_away
        self.stadium_name = stadium_name
        self.stadium = STADIUM_MODIFIERS.get(stadium_name, {"hit_mult": 1.0, "hr_mult": 1.0})
        self.last_results = None
        self.save_cache = save_cache
        self.cache_filename = cache_filename

    def play_game(self):
        engine = GameEngine(self.home_team, self.away_team, self.stadium)
        home_score, away_score = 0, 0
        home_hr, away_hr = 0, 0
        home_hits, away_hits = 0, 0
        home_so, away_so = 0, 0

        for inning in range(1, 10):
            loc_aw, loc_hr, loc_hits, loc_so = engine.simulate_half_inning(self.away_team, self.home_team)
            away_score += loc_aw
            away_hr += loc_hr
            away_hits += loc_hits
            away_so += loc_so
            
            if inning == 9 and home_score > away_score:
                break
                
            loc_home, loc_hr, loc_hits, loc_so = engine.simulate_half_inning(self.home_team, self.away_team)
            home_score += loc_home
            home_hr += loc_hr
            home_hits += loc_hits
            home_so += loc_so
            
            if inning == 9 and away_score > home_score:
                break

        while home_score == away_score:
            loc_aw, loc_hr, loc_hits, loc_so = engine.simulate_half_inning(self.away_team, self.home_team)
            away_score += loc_aw
            away_hr += loc_hr
            away_hits += loc_hits
            away_so += loc_so
            loc_home, loc_hr, loc_hits, loc_so = engine.simulate_half_inning(self.home_team, self.away_team)
            home_score += loc_home
            home_hr += loc_hr
            home_hits += loc_hits
            home_so += loc_so

        return home_score, away_score, home_hr, away_hr, home_hits, away_hits, home_so, away_so

    def run(self, trials=1000):
        player_totals = {}

        def init_player_tracker(team):
            for p in team.roster:
                if p.name not in player_totals:
                    player_totals[p.name] = {
                        "ab": 0, "h": 0, "hr": 0, "rbi": 0, "so": 0, "pa": 0,
                        "runs": 0, "ip_outs": 0, "ip_bf": 0, "ip_ha": 0, "ip_so": 0,
                        "runs_allowed": 0, "walks_allowed": 0, "hits_allowed": 0,
                        "dp": 0, "tp": 0, "def_dp": 0, "def_tp": 0,
                    }

        init_player_tracker(self.home_team)
        init_player_tracker(self.away_team)

        player_trial_lists = {}
        def init_player_trial_lists(team):
            for p in team.roster:
                if p.name not in player_trial_lists:
                    player_trial_lists[p.name] = {
                        "h": [], "hr": [], "rbi": [], "runs": [], "so": [], "ab": [], "pa": [],
                        "hits_allowed": [], "runs_allowed": [], "so_pitched": [], "outs_recorded": [],
                        "dp": [], "tp": [], "def_dp": [], "def_tp": [],
                    }
        init_player_trial_lists(self.home_team)
        init_player_trial_lists(self.away_team)

        home_wins, away_wins = 0, 0
        
        home_runs_list = []
        away_runs_list = []
        total_runs_list = []
        home_hr_list = []
        away_hr_list = []
        total_hr_list = []
        home_hits_list = []
        away_hits_list = []
        total_hits_list = []
        home_k_list = []
        away_k_list = []
        total_k_list = []

        for _ in range(trials):
            self.home_team.reset_pitchers()
            self.home_team.reset_batters()
            self.away_team.reset_pitchers()
            self.away_team.reset_batters()
            
            for p in self.home_team.roster + self.away_team.roster:
                p.reset_game_stats()

            h_score, a_score, h_hr, a_hr, h_h, a_h, h_k, a_k = self.play_game()
            
            home_runs_list.append(h_score)
            away_runs_list.append(a_score)
            total_runs_list.append(h_score + a_score)
            
            home_hr_list.append(h_hr)
            away_hr_list.append(a_hr)
            total_hr_list.append(h_hr + a_hr)

            home_hits_list.append(h_h)
            away_hits_list.append(a_h)
            total_hits_list.append(h_h + a_h)

            home_k_list.append(h_k)
            away_k_list.append(a_k)
            total_k_list.append(h_k + a_k)

            if h_score > a_score:
                home_wins += 1
            else:
                away_wins += 1

            for team in [self.home_team, self.away_team]:
                for p in team.roster:
                    player_totals[p.name]["ab"] += p.ab
                    player_totals[p.name]["h"] += p.hits
                    player_totals[p.name]["hr"] += p.home_runs
                    player_totals[p.name]["rbi"] += p.rbi
                    player_totals[p.name]["so"] += p.so
                    player_totals[p.name]["pa"] += p.pa
                    player_totals[p.name]["runs"] += p.runs_scored
                    player_totals[p.name]["ip_outs"] += p.outs_recorded
                    player_totals[p.name]["runs_allowed"] += p.runs_allowed
                    player_totals[p.name]["walks_allowed"] += getattr(p, "walks_allowed", 0)
                    player_totals[p.name]["hits_allowed"] += getattr(p, "hits_allowed", 0)
                    player_totals[p.name]["ip_bf"] += p.batters_faced
                    player_totals[p.name]["ip_ha"] += p.hits_allowed
                    player_totals[p.name]["ip_so"] += p.so_pitched
                    player_totals[p.name]["dp"] += getattr(p, "dp", 0)
                    player_totals[p.name]["tp"] += getattr(p, "tp", 0)
                    player_totals[p.name]["def_dp"] += getattr(p, "def_dp", 0)
                    player_totals[p.name]["def_tp"] += getattr(p, "def_tp", 0)

                    player_trial_lists[p.name]["h"].append(p.hits)
                    player_trial_lists[p.name]["hr"].append(p.home_runs)
                    player_trial_lists[p.name]["rbi"].append(p.rbi)
                    player_trial_lists[p.name]["runs"].append(p.runs_scored)
                    player_trial_lists[p.name]["so"].append(p.so)
                    player_trial_lists[p.name]["ab"].append(p.ab)
                    player_trial_lists[p.name]["pa"].append(p.pa)
                    player_trial_lists[p.name]["hits_allowed"].append(getattr(p, "hits_allowed", 0))
                    player_trial_lists[p.name]["runs_allowed"].append(getattr(p, "runs_allowed", 0))
                    player_trial_lists[p.name]["so_pitched"].append(getattr(p, "so_pitched", 0))
                    player_trial_lists[p.name]["outs_recorded"].append(getattr(p, "outs_recorded", 0))
                    player_trial_lists[p.name]["dp"].append(getattr(p, "dp", 0))
                    player_trial_lists[p.name]["tp"].append(getattr(p, "tp", 0))
                    player_trial_lists[p.name]["def_dp"].append(getattr(p, "def_dp", 0))
                    player_trial_lists[p.name]["def_tp"].append(getattr(p, "def_tp", 0))

        self.last_results = {
            "home_runs": home_runs_list,
            "away_runs": away_runs_list,
            "total_runs": total_runs_list,
            "home_hr": home_hr_list,
            "away_hr": away_hr_list,
            "total_hr": total_hr_list,
            "home_hits": home_hits_list,
            "away_hits": away_hits_list,
            "total_hits": total_hits_list,
            "home_k": home_k_list,
            "away_k": away_k_list,
            "total_k": total_k_list,
        }

        player_averages = {}
        for name, totals in player_totals.items():
            t = max(1, trials)
            ab = totals["ab"]
            h = totals["h"]
            outs_recorded = totals["ip_outs"]
            ip = outs_recorded / 3.0
            runs_allowed = totals["runs_allowed"]
            walks_allowed = totals["walks_allowed"]
            hits_allowed = totals["hits_allowed"]
            bf = totals["ip_bf"]
            so_pitched = totals["ip_so"]

            player_averages[name] = {
                "avg_AB": ab / t,
                "avg_H": h / t,
                "avg_HR": totals["hr"] / t,
                "avg_RBI": totals["rbi"] / t,
                "avg_R": totals["runs"] / t,
                "avg_SO": totals["so"] / t,
                "BA": (h / ab) if ab > 0 else 0.0,
                "avg_IP": ip / t,
                "avg_BF": bf / t,
                "avg_H_allowed": hits_allowed / t,
                "avg_R_allowed": runs_allowed / t,
                "avg_SO_pitched": so_pitched / t,
                "ERA": ((runs_allowed * 9) / ip) if ip > 0 else 0.0,
                "WHIP": ((walks_allowed + totals["ip_ha"]) / ip) if ip > 0 else 0.0,
                "avg_DP": totals["dp"] / t,
                "avg_TP": totals["tp"] / t,
                "avg_def_DP": totals["def_dp"] / t,
                "avg_def_TP": totals["def_tp"] / t,
            }

        results = {
            "home_win_pct": (home_wins / trials) * 100,
            "away_win_pct": (away_wins / trials) * 100,
            "home_avg_runs": statistics.mean(home_runs_list),
            "away_avg_runs": statistics.mean(away_runs_list),
            "total_avg_runs": statistics.mean(total_runs_list),
            "home_median_runs": statistics.median(home_runs_list),
            "away_median_runs": statistics.median(away_runs_list),
            "total_median_runs": statistics.median(total_runs_list),
            "home_avg_hr": statistics.mean(home_hr_list),
            "away_avg_hr": statistics.mean(away_hr_list),
            "total_avg_hr": statistics.mean(total_hr_list),
            "home_median_hr": statistics.median(home_hr_list),
            "away_median_hr": statistics.median(away_hr_list),
            "total_median_hr": statistics.median(total_hr_list),
            "home_avg_hits": statistics.mean(home_hits_list),
            "away_avg_hits": statistics.mean(away_hits_list),
            "total_avg_hits": statistics.mean(total_hits_list),
            "home_median_hits": statistics.median(home_hits_list),
            "away_median_hits": statistics.median(away_hits_list),
            "total_median_hits": statistics.median(total_hits_list),
            "home_avg_k": statistics.mean(home_k_list),
            "away_avg_k": statistics.mean(away_k_list),
            "total_avg_k": statistics.mean(total_k_list),
            "home_median_k": statistics.median(home_k_list),
            "away_median_k": statistics.median(away_k_list),
            "total_median_k": statistics.median(total_k_list),
            "player_averages": player_averages,
            "player_trials": player_trial_lists
        }

        if self.save_cache:
                cache_data = {
                    "results": results,
                    "last_results": self.last_results,
                    "home_team": self.home_team.name,
                    "away_team": self.away_team.name,
                    "stadium": self.stadium_name
                }
                with open(self.cache_filename, "wb") as f:
                    pickle.dump(cache_data, f)

        return results

    def get_runs_percentile(self, count, category="total"):
        if not self.last_results:
            raise ValueError("Run the simulation first before checking percentiles.")
        
        key_map = {"home": "home_runs", "away": "away_runs", "total": "total_runs"}
        data = self.last_results[key_map.get(category, "total_runs")]
        
        below_count = sum(1 for x in data if x <= count)
        return (below_count / len(data)) * 100

    def get_hr_percentile(self, count, category="total"):
        if not self.last_results:
            raise ValueError("Run the simulation first before checking percentiles.")
        
        key_map = {"home": "home_hr", "away": "away_hr", "total": "total_hr"}
        data = self.last_results[key_map.get(category, "total_hr")]
        
        below_count = sum(1 for x in data if x <= count)
        return (below_count / len(data)) * 100

    def print_summary(self, results):
        print("=" * 100)
        print(f"Monte Carlo Simulation Results: ({self.away_team.name} @ {self.home_team.name} in {self.stadium_name})")
        print("=" * 100)
        print(f"Away ({self.away_team.name}) Win %: {results['away_win_pct']:.1f}%")
        print(f"Home ({self.home_team.name}) Win %: {results['home_win_pct']:.1f}%")
        print("-" * 100)
        print(f"Runs/Game       | Away: {results['away_avg_runs']:.2f} (Med: {results['away_median_runs']}) | Home: {results['home_avg_runs']:.2f} (Med: {results['home_median_runs']}) | Total: {results['total_avg_runs']:.2f} (Med: {results['total_median_runs']})")
        print(f"Hits/Game      | Away: {results['away_avg_hits']:.2f} (Med: {results['away_median_hits']}) | Home: {results['home_avg_hits']:.2f} (Med: {results['home_median_hits']}) | Total: {results['total_avg_hits']:.2f} (Med: {results['total_median_hits']})")
        print(f"Home Runs/Game  | Away: {results['away_avg_hr']:.2f} (Med: {results['away_median_hr']}) | Home: {results['home_avg_hr']:.2f} (Med: {results['home_median_hr']}) | Total: {results['total_avg_hr']:.2f} (Med: {results['total_median_hr']})")
        print(f"Strikeouts/Game | Away: {results['away_avg_k']:.2f} (Med: {results['away_median_k']}) | Home: {results['home_avg_k']:.2f} (Med: {results['home_median_k']}) | Total: {results['total_avg_k']:.2f} (Med: {results['total_median_k']})")
        print("=" * 100)

        for team in [self.away_team, self.home_team]:
            print(f"\n\nExpected Per-Game Player Stats: {team.name}")
            print(f"{'Player Name':<18} | {'AB':<5} | {'H':<5} | {'BA':<6} | {'HR':<5} | {'RBI':<5} | {'R':<5} | {'SO':<5}")
            print("-" * 65)
            
            for player in team.roster:
                p_stats = results["player_averages"].get(player.name, {})
                ab = p_stats.get("avg_AB", 0)
                h = p_stats.get("avg_H", 0)
                ba = p_stats.get("BA", 0)
                hr = p_stats.get("avg_HR", 0)
                rbi = p_stats.get("avg_RBI", 0)
                runs = p_stats.get("avg_R", 0)
                so = p_stats.get("avg_SO", 0)

                print(f"{player.name:<18} | {ab:<5.2f} | {h:<5.2f} | {ba:<6.3f} | {hr:<5.2f} | {rbi:<5.2f} | {runs:<5.2f} | {so:<5.2f}")
            
            print("-" * 65)
            print(f"Pitching Rotation Statistics: {team.name}")
            print(f"{'Pitcher Name':<18} | {'IP':<6} | {'H':<5} | {'R':<5} | {'ER':<5} | {'SO':<5} | {'ERA':<6} | {'WHIP':<6}")
            print("-" * 65)

            for pitcher in team.pitching_order:
                p_stats = results["player_averages"].get(pitcher.name, {})
                ip = p_stats.get("avg_IP", 0)
                h = p_stats.get("avg_H_allowed", 0)
                r = p_stats.get("avg_R_allowed", 0)
                so = p_stats.get("avg_SO_pitched", 0)
                era = p_stats.get("ERA", 0)
                whip = p_stats.get("WHIP", 0)

                if p_stats.get("avg_BF", 0) > 0:
                    print(f"{pitcher.name:<18} | {ip:<6.1f} | {h:<5.2f} | {r:<5.2f} | {r:<5.2f} | {so:<5.2f} | {era:<6.2f} | {whip:<6.2f}")
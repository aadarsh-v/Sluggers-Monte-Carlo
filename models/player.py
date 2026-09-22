from data.league_stats import LEAGUE_AVG_BA, LEAGUE_AVG_K, LEAGUE_AVG_HR, LEAGUE_HIT_SHARES, LEAGUE_OUT_SHARES
from utils.math_utils import regress_to_mean

class Player:
    def __init__(self, raw_data, is_pitcher=False):
        self.name = raw_data["name"]
        self.is_pitcher = is_pitcher

        self.max_stamina = raw_data.get("Stamina", 40)
        self.current_stamina = self.max_stamina
        
        # Batter metrics
        pa = raw_data.get("PA", 1)
        ab = raw_data.get("AB", 1)
        self.ba = regress_to_mean(raw_data.get("H", 0), ab, LEAGUE_AVG_BA, weight=4)
        self.k_rate = regress_to_mean(raw_data.get("SO", 0), ab, LEAGUE_AVG_K, weight=4)
        self.dp_rate = regress_to_mean(raw_data.get("DP Into", 0), pa, 0.038, weight=10)
        self.tp_rate = regress_to_mean(raw_data.get("TP Into", 0), pa, 0.002)
        
        # Hit distribution shares
        total_hits = max(1, raw_data.get("H", 0))
        self.hit_shares = {
            "1B": regress_to_mean(raw_data.get("1B", 0), total_hits, LEAGUE_HIT_SHARES["1B"], weight=5),
            "2B": regress_to_mean(raw_data.get("2B", 0), total_hits, LEAGUE_HIT_SHARES["2B"], weight=5),
            "3B": regress_to_mean(raw_data.get("3B", 0), total_hits, LEAGUE_HIT_SHARES["3B"], weight=5),
            "HR": regress_to_mean(raw_data.get("HR", 0), total_hits, LEAGUE_HIT_SHARES["HR"], weight=2),
        }
        s_sum = sum(self.hit_shares.values())
        self.hit_shares = {k: v / s_sum for k, v in self.hit_shares.items()}
        
        # Out shares
        self.out_shares = {
            "SO": self.k_rate,
            "Std_Out": max(0.01, 1.0 - self.k_rate - self.dp_rate - self.tp_rate),
            "DP": self.dp_rate,
            "TP": self.tp_rate
        }
        
        # Pitcher metrics
        self.raw_bf = raw_data.get("BF", 0)
        self.raw_ha = raw_data.get("H_allowed", 0)
        pitcher_weight = 75
        if self.is_pitcher and self.raw_bf > 0:
            self.pitcher_h_bf = regress_to_mean(raw_data.get("H_allowed", 0), self.raw_bf, LEAGUE_AVG_BA, weight=pitcher_weight)
            self.pitcher_k_bf = regress_to_mean(raw_data.get("SO_allowed", 0), self.raw_bf, LEAGUE_AVG_K, weight=40)
            self.pitcher_hr_allowed_share = regress_to_mean(raw_data.get("HR_allowed", 0), max(1, raw_data.get("H_allowed", 0)), LEAGUE_AVG_HR, weight=200)
        else:
            self.pitcher_h_bf, self.pitcher_k_bf, self.pitcher_hr_allowed_share = LEAGUE_AVG_BA, LEAGUE_OUT_SHARES["SO"], LEAGUE_AVG_HR

        # Fielding metrics (from raw_data)
        self.raw_errors = raw_data.get("Errors", 0)
        self.raw_dp_contributed = raw_data.get("DP", 0)
        self.raw_tp_contributed = raw_data.get("TP", 0)

        self.reset_game_stats()

    def reset_game_stats(self):
        # Hitter tracking
        self.pa = 0
        self.ab = 0
        self.hits = 0
        self._1b = 0
        self._2b = 0
        self._3b = 0
        self.home_runs = 0
        self.so = 0
        self.runs_scored = 0
        self.rbi = 0
        self.dp = 0
        self.tp = 0

        # Pitcher tracking
        self.batters_faced = 0
        self.outs_recorded = 0
        self.hits_allowed = 0
        self.runs_allowed = 0
        self.so_pitched = 0
        self.hr_allowed = 0
        self.current_stamina = self.max_stamina
        self.def_dp = 0
        self.def_tp = 0

        # Fielding tracking
        self.errors = 0

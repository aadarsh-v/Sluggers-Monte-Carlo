from models.player import Player

class Team:
    def __init__(self, name, raw_roster, pitching_order_names):
        self.name = name
        self.roster = [Player(p, is_pitcher=(p["name"] in pitching_order_names)) for p in raw_roster]
        self.lineup = list(self.roster)
        player_map = {p.name: p for p in self.roster}

        self.pitching_order = [player_map[name] for name in pitching_order_names if name in player_map]
        if not self.pitching_order:
            self.pitching_order = [p for p in self.roster if p.is_pitcher]
            if not self.pitching_order:
                self.pitching_order = [self.roster[0]]

        self.current_pitcher_idx = 0
        self.current_pitcher = self.pitching_order[self.current_pitcher_idx]
        self.current_batter_idx = 0

    @property
    def defensive_dp_rate(self):
        total_raw_dp = sum(p.raw_dp_contributed for p in self.roster)
        actual_dps = total_raw_dp / 2.0
        total_bf = sum(p.raw_bf for p in self.pitching_order)
        total_ha = sum(p.raw_ha for p in self.pitching_order)
        if total_bf == 0:
            total_bf = max(100, len(self.roster) * 35) 
        return actual_dps / (total_bf - total_ha)

    @property
    def defensive_tp_rate(self):
        total_raw_tp = sum(p.raw_tp_contributed for p in self.roster)
        actual_tps = total_raw_tp / 3.0
        total_bf = sum(p.raw_bf for p in self.pitching_order)
        total_ha = sum(p.raw_ha for p in self.pitching_order)
        if total_bf == 0:
            total_bf = max(100, len(self.roster) * 35)
        return actual_tps / (total_bf - total_ha)

    def get_next_batter(self):
        batter = self.lineup[self.current_batter_idx]
        self.current_batter_idx = (self.current_batter_idx + 1) % len(self.lineup)
        return batter

    def check_and_swap_pitcher(self):
        """Swaps to the next pitcher in the pitching order if current pitcher is out of stamina."""
        if self.current_pitcher.current_stamina <= 0:
            if self.current_pitcher_idx < len(self.pitching_order) - 1:
                self.current_pitcher_idx += 1
            else:
                self.current_pitcher_idx = len(self.pitching_order) - 1
            self.current_pitcher = self.pitching_order[self.current_pitcher_idx]
        return self.current_pitcher

    def reset_pitchers(self):
        self.current_pitcher_idx = 0
        self.current_pitcher = self.pitching_order[0]
        for p in self.pitching_order:
            p.current_stamina = p.max_stamina

    def reset_batters(self):
        self.current_batter_idx = 0
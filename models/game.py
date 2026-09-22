import math
import random
from utils.math_utils import calculate_log_odds_matchup, calculate_multiplicative_matchup, calculate_pitcher_weighted_matchup
from data.league_stats import LEAGUE_AVG_BA, LEAGUE_AVG_HR, LEAGUE_AVG_K, LEAGUE_HIT_SHARES, LEAGUE_OUT_SHARES

class GameEngine:
    def __init__(self, home_team, away_team, stadium_modifier):
        self.home_team = home_team
        self.away_team = away_team
        self.stadium = stadium_modifier
        
        rand_mult = self.stadium.get("randomness_mult", 1.0)
        
        # Scale luck variance using the stadium randomness factor (i.e. for stadiums with more hazards)
        self.home_luck = random.gauss(1.0, 0.1 * rand_mult)
        self.away_luck = random.gauss(1.0, 0.1 * rand_mult)

    def get_random_hit_type(self, batter, pitcher):
        # Log5 matchup probability for Home Runs scaled with a nonlinear HR multiplier and triples multiplier. 
        b = max(0.001, min(0.999, batter.hit_shares["HR"]))
        p = max(0.001, min(0.999, pitcher.pitcher_hr_allowed_share))
        la = max(0.001, min(0.999, LEAGUE_AVG_HR))

        odds_b = b / (1 - b)
        odds_p = p / (1 - p)
        odds_la = la / (1 - la)

        matchup_odds = ((odds_b * odds_p) / odds_la) ** 0.96

        base_hr_mult = self.stadium.get("hr_mult", 1.0)        
        if base_hr_mult > 1.0:
            # Low-HR hitters are boosted more in HR friendly stadiums
            scaling_factor = 1.0 + (max(0.0, 1.0 - (b / LEAGUE_AVG_HR)) * 0.5)
            stadium_hr_mult = 1.0 + ((base_hr_mult - 1.0) * scaling_factor)
        else:
            # Low-HR hitters are penalized more in HR unfriendly stadiums
            relative_power = b / LEAGUE_AVG_HR
            scaling_factor = 1.1 + (0.3 * min(4.0, relative_power))
            stadium_hr_mult = max(0.001, base_hr_mult ** scaling_factor)

        adjusted_odds = matchup_odds * stadium_hr_mult
        hr_prob = adjusted_odds / (1 + adjusted_odds)

        if random.random() < hr_prob:
            return "HR"
        
        remaining_types = ["1B", "2B", "3B"]
        weights = []
        for t in remaining_types:
            share = batter.hit_shares[t]
            if t == "2B":
                share *= 1.55
            if t == "3B":
                share *= self.stadium.get("triples_mult", 1.0) * 1.55
            weights.append(share)
            
        return random.choices(remaining_types, weights=weights)[0]

    def resolve_hit(self, batter, pitcher, bases, hit_type):
        runs = 0
        rbi_count = 0
        is_hr = False
        
        runner_on_1st = bases[0]
        runner_on_2nd = bases[1]
        runner_on_3rd = bases[2]

        if hit_type == "1B":
            if runner_on_3rd:
                runner_on_3rd.runs_scored += 1
                runs += 1
                rbi_count += 1
            if runner_on_2nd:
                if random.random() <= 0.75:
                    runner_on_2nd.runs_scored += 1
                    runs += 1
                    rbi_count += 1
                    bases = [batter, runner_on_1st, None]
                else:
                    bases = [batter, runner_on_1st, runner_on_2nd]
            bases = [batter, runner_on_1st, None]
            batter._1b += 1

        elif hit_type == "2B":
            if runner_on_3rd:
                runner_on_3rd.runs_scored += 1
                runs += 1
                rbi_count += 1
            if runner_on_2nd:
                runner_on_2nd.runs_scored += 1
                runs += 1
                rbi_count += 1
            third_base_runner = None
            if runner_on_1st:
                if random.random() <= 0.75:
                    runner_on_1st.runs_scored += 1
                    runs += 1
                    rbi_count += 1
                else:
                    third_base_runner = runner_on_1st
            bases = [None, batter, third_base_runner]
            batter._2b += 1

        elif hit_type == "3B":
            for runner in [runner_on_1st, runner_on_2nd, runner_on_3rd]:
                if runner:
                    runner.runs_scored += 1
                    runs += 1
                    rbi_count += 1
            bases = [None, None, batter]
            batter._3b += 1

        elif hit_type == "HR":
            for runner in [runner_on_1st, runner_on_2nd, runner_on_3rd]:
                if runner:
                    runner.runs_scored += 1
                    runs += 1
                    rbi_count += 1
            batter.runs_scored += 1
            runs += 1
            rbi_count += 1
            bases = [None, None, None]
            batter.home_runs += 1
            is_hr = True

        batter.hits += 1
        batter.ab += 1
        batter.pa += 1
        batter.rbi += rbi_count
        
        pitcher.hits_allowed += 1
        pitcher.batters_faced += 1
        pitcher.runs_allowed += runs
        if runs > 0:
            pitcher.current_stamina -= runs * 12
        else:
            pitcher.current_stamina -= 3
        pitcher.current_stamina = max(0, pitcher.current_stamina)

        if hit_type == "HR":
            pitcher.hr_allowed += 1

        return runs, bases, is_hr

    def resolve_out(self, batter, pitcher, bases, outs, pitching_team):
        batter.pa += 1
        pitcher.batters_faced += 1
        
        # raw_weights = {}
        # runners_on_base = sum(1 for b in bases if b is not None)
        # can_hit_into_dp = (outs < 2) and (bases[0] is not None)
        # can_hit_into_tp = (outs == 0) and (runners_on_base >= 2)

        # pitcher_k = getattr(pitcher, 'pitcher_k_bf', LEAGUE_OUT_SHARES["SO"])
        # team_dp_metric = getattr(pitching_team, 'defensive_dp_rate', LEAGUE_OUT_SHARES["DP"])
        # team_tp_metric = getattr(pitching_team, 'defensive_tp_rate', LEAGUE_OUT_SHARES["TP"])
        # pitcher_std_out_metric = max(0.01, 1.0 - pitcher_k - team_dp_metric - team_tp_metric)

        # league_k = LEAGUE_OUT_SHARES["SO"]
        # league_dp = LEAGUE_OUT_SHARES["DP"]
        # league_tp = LEAGUE_OUT_SHARES["TP"]
        # league_std_out = max(0.01, 1.0 - league_k - league_dp - league_tp)

        # std_out_weight = calculate_log_odds_matchup(
        #     batter.out_shares["Std_Out"], pitcher_std_out_metric, league_std_out
        # )
        # dp_weight = calculate_log_odds_matchup(
        #     batter.out_shares["DP"], team_dp_metric, league_dp
        # )
        # if not can_hit_into_dp:
        #     dp_weight = 0.0
        # else:
        #     dp_weight = dp_weight * (runners_on_base * 3)
        # tp_weight = calculate_log_odds_matchup(
        #     batter.out_shares["TP"], team_tp_metric, league_tp
        # )
        # if not can_hit_into_tp:
        #     tp_weight = 0.0
        # else:
        #     tp_weight = tp_weight * runners_on_base * 4

        # raw_weights["Std_Out"] = max(0.01, std_out_weight)
        # raw_weights["DP"] = max(0.0, dp_weight)
        # raw_weights["TP"] = max(0.0, tp_weight)
    
        # total_weight = sum(raw_weights.values())
        # chances = {k: v / total_weight for k, v in raw_weights.items()}
        # chosen_out = random.choices(list(chances.keys()), weights=list(chances.values()), k=1)[0]

        raw_weights = {}
        runners_on_base = sum(1 for b in bases if b is not None)
        can_hit_into_dp = (outs < 2) and (bases[0] is not None)
        can_hit_into_tp = (outs == 0) and (runners_on_base >= 2)

        pitcher_k = getattr(pitcher, 'pitcher_k_bf', LEAGUE_OUT_SHARES["SO"])
        team_dp_metric = getattr(pitching_team, 'defensive_dp_rate', LEAGUE_OUT_SHARES["DP"])
        team_tp_metric = getattr(pitching_team, 'defensive_tp_rate', LEAGUE_OUT_SHARES["TP"])
        pitcher_std_out_metric = max(0.01, 1.0 - pitcher_k - team_dp_metric - team_tp_metric)

        league_k = LEAGUE_OUT_SHARES["SO"]
        league_dp = LEAGUE_OUT_SHARES["DP"]
        league_tp = LEAGUE_OUT_SHARES["TP"]
        league_std_out = max(0.01, 1.0 - league_k - league_dp - league_tp)

        std_out_weight = calculate_log_odds_matchup(
            batter.out_shares["Std_Out"], pitcher_std_out_metric, league_std_out
        )

        if not can_hit_into_dp:
            dp_weight = 0.0
        else:
            b_factor = (batter.out_shares["DP"] / max(0.001, league_dp)) ** 1.25
            d_factor = (team_dp_metric / max(0.001, league_dp)) ** 3.25
            runner_scaling = math.sqrt(runners_on_base)
            dp_weight = league_dp * (b_factor * d_factor) * runner_scaling * 25.5

        if not can_hit_into_tp:
            tp_weight = 0.0
        else:
            b_factor_tp = (batter.out_shares["TP"] / max(0.0001, league_tp)) ** 1.25
            d_factor_tp = (team_tp_metric / max(0.0001, league_tp)) ** 3.25
            runner_scaling_tp = math.sqrt(runners_on_base)
            tp_weight = league_tp * (b_factor_tp * d_factor_tp) * runner_scaling_tp * 50.5

        raw_weights["Std_Out"] = max(0.01, std_out_weight)
        raw_weights["DP"] = max(0.0, dp_weight)
        raw_weights["TP"] = max(0.0, tp_weight)
    
        total_weight = sum(raw_weights.values())
        chances = {k: v / total_weight for k, v in raw_weights.items()}
        chosen_out = random.choices(list(chances.keys()), weights=list(chances.values()), k=1)[0]
        
        runs = 0
        pitcher.outs_recorded += 1

        if chosen_out == "Std_Out":
            outs += 1
            batter.ab += 1
            if bases[2] is not None and outs < 3 and random.random() <= 0.75:   # Sacfly probability
                bases[2].runs_scored += 1
                runs += 1
                batter.rbi += 1
                bases[2] = None
                pitcher.runs_allowed += 1
            elif bases[1] is not None and bases[2] is None and outs < 3 and random.random() <= 0.5:
                bases[2] = bases[1]
                bases[1] = None

        elif chosen_out == "DP":
            outs += 2
            pitcher.outs_recorded += 1
            batter.ab += 1
            batter.dp += 1
            pitcher.def_dp += 1
            if bases[1] is not None:
                bases[1] = None
            elif bases[2] is not None:
                bases[2] = None
            elif bases[0] is not None:
                bases[0] = None

        elif chosen_out == "TP":
            outs += 3
            pitcher.outs_recorded += 2
            batter.ab += 1
            batter.tp += 1
            pitcher.def_tp += 1
            bases = [None, None, None]

        return runs, bases, outs

    def simulate_half_inning(self, batting_team, pitching_team):
        outs, runs, home_runs, hits, strikeouts = 0, 0, 0, 0, 0
        bases = [None, None, None] 

        team_luck = self.home_luck if batting_team == self.home_team else self.away_luck
        
        while outs < 3:
            pitcher = pitching_team.check_and_swap_pitcher()
            batter = batting_team.get_next_batter()

            # runners_on_base = sum(1 for b in bases if b is not None)
            # if runners_on_base == 0:
            #     runners_mult = 0.85
            # elif runners_on_base == 1:
            #     runners_mult = 1.0
            # elif runners_on_base == 2:
            #     runners_mult = 1.1
            # else:  # bases loaded (3 runners)
            #     runners_mult = 1.2

            # matchup_hit_chance = calculate_log_odds_matchup(
            #     batter.ba, pitcher.pitcher_h_bf, LEAGUE_AVG_BA
            # ) * self.stadium.get("hit_mult", 1.0) * team_luck
            matchup_hit_chance = calculate_pitcher_weighted_matchup(
                batter.ba, pitcher.pitcher_h_bf, LEAGUE_AVG_BA, pitcher_weight_bias=1.25
            ) * self.stadium.get("hit_mult", 1.0) * team_luck
            matchup_so_prob = calculate_log_odds_matchup(
                batter.out_shares["SO"], pitcher.pitcher_k_bf, LEAGUE_AVG_K
            )
            weight_hit = max(0.001, matchup_hit_chance)
            weight_so = max(0.001, matchup_so_prob)
            weight_bip = max(0.001, 1.0 - (weight_hit + weight_so))
            
            outcomes = ["HIT", "SO", "BIP"]
            weights = [weight_hit, weight_so, weight_bip]
            pa_result = random.choices(outcomes, weights=weights, k=1)[0]

            if pa_result == "HIT":
                hit_type = self.get_random_hit_type(batter, pitcher)
                r, bases, is_hr = self.resolve_hit(batter, pitcher, bases, hit_type)
                runs += r
                hits += 1
                if is_hr:
                    home_runs += 1
            elif pa_result == "SO":
                batter.pa += 1
                pitcher.batters_faced += 1
                outs += 1
                batter.ab += 1
                batter.so += 1
                pitcher.so_pitched += 1
                pitcher.outs_recorded += 1
                strikeouts += 1
            else:
                r, bases, outs = self.resolve_out(batter, pitcher, bases, outs, pitching_team)
                runs += r
                
        return runs, home_runs, hits, strikeouts
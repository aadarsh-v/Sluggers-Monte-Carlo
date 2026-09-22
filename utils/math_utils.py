def regress_to_mean(player_value, opportunity_volume, league_baseline, weight=50):
    return (player_value + (league_baseline * weight)) / (opportunity_volume + weight)

def calculate_log_odds_matchup(batter_stat, pitcher_stat, league_avg, sensitivity=1.0):
    """Log5 method but with an extra sensitivity modifier to (artificially) reflect observed league averages."""
    b = max(0.001, min(0.999, batter_stat))
    p = max(0.001, min(0.999, pitcher_stat))
    la = max(0.001, min(0.999, league_avg))
    
    odds_b = b / (1 - b)
    odds_p = p / (1 - p)
    odds_la = la / (1 - la)
    
    matchup_odds = ((odds_b * odds_p) / odds_la) ** sensitivity
    return matchup_odds / (1 + matchup_odds)

def calculate_pitcher_weighted_matchup(batter_stat, pitcher_stat, league_avg, pitcher_weight_bias=1.3):
    """
    Log5 variant that gives more weight to the pitcher's capability 
    to dictate game outcomes compared to the individual batter.
    """
    b = max(0.001, min(0.999, batter_stat))
    p = max(0.001, min(0.999, pitcher_stat))
    la = max(0.001, min(0.999, league_avg))
    
    odds_b = b / (1 - b)
    odds_p = p / (1 - p)
    odds_la = la / (1 - la)
    
    # Weight the pitcher's odds more heavily than the batter's
    matchup_odds = ((odds_b ** (2.0 - pitcher_weight_bias)) * (odds_p ** pitcher_weight_bias)) / odds_la
    return matchup_odds / (1 + matchup_odds)

def calculate_multiplicative_matchup(batter_stat, pitcher_stat, league_avg):
    """Alternative multiplicative ratio."""
    if league_avg <= 0:
        return batter_stat
    
    raw_prob = (batter_stat * pitcher_stat) / league_avg
    return max(0.001, min(0.999, raw_prob))
LEAGUE_AVG_BA = 0.375   # BA or OBP
LEAGUE_AVG_K = 0.13     # K/BF
LEAGUE_AVG_HR = 0.061   # HR/H

LEAGUE_HIT_SHARES = {"1B": 0.853, "2B": 0.069, "3B": 0.017, "HR": 0.061}        # As percentages of hits.
LEAGUE_OUT_SHARES = {"SO": 0.200, "Std_Out": 0.667, "DP": 0.122, "TP": 0.011}    # As percentages of outs.

STADIUM_MODIFIERS = {
    "Peach_Ice_Day": {"hit_mult": 1.02, "hr_mult": 0.4, "triples_mult": 2.50, "randomness_mult": 0.7},
    "Peach_Ice_Night": {"hit_mult": 1.045, "hr_mult": 0.4, "triples_mult": 3.00, "randomness_mult": 1.0},
    "Luigis_Mansion": {"hit_mult": 0.975, "hr_mult": 0.8, "triples_mult": 1.00, "randomness_mult": 0.7},
    "Mario_Stadium": {"hit_mult": 1.00, "hr_mult": 1.00, "triples_mult": 1.00, "randomness_mult": 0.5},
    "DK_Jungle_Day": {"hit_mult": 1.015, "hr_mult": 1.1, "triples_mult": 1.00, "randomness_mult": 1.3},
    "DK_Jungle_Night": {"hit_mult": 1.00, "hr_mult": 1.1, "triples_mult": 1.00, "randomness_mult": 1.0},
    "Daisy_Cruiser_Day": {"hit_mult": 0.99, "hr_mult": 2.25, "triples_mult": 0.40, "randomness_mult": 1.3},
    "Daisy_Cruiser_Night": {"hit_mult": 0.98, "hr_mult": 2.70, "triples_mult": 0.40, "randomness_mult": 1.3},
    "Bowser_Castle": {"hit_mult": 1.00, "hr_mult": 0.9, "triples_mult": 1.50, "randomness_mult": 1.45},
    "Bowser_Jr_Playroom": {"hit_mult": 0.965, "hr_mult": 0.7, "triples_mult": 0.7, "randomness_mult": 0.7},
    "Wario_City_Day": {"hit_mult": 1.015, "hr_mult": 1.3, "triples_mult": 1.25, "randomness_mult": 0.85},
    "Wario_City_Night": {"hit_mult": 1.03, "hr_mult": 1.3, "triples_mult": 2.00, "randomness_mult": 1.45},
    "Yoshi_Park_Day": {"hit_mult": 1.00, "hr_mult": 1.0, "triples_mult": 1.25, "randomness_mult": 1.0},
    "Yoshi_Park_Night": {"hit_mult": 1.015, "hr_mult": 1.15, "triples_mult": 1.3, "randomness_mult": 1.8},
}
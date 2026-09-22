from models.team import Team
from simulation import MonteCarloSimulation
import pandas as pd

blues_pitchers = ["Peach", "Luigi", "Rainer", "The Sailor"]
custoadians_pitchers = ["Donkey Kong", "Toadsworth", "Curtis S"]
fighters_pitchers = ["Bowser", "Jinu Kim", "Blue Magikoopa"]
top1_pitchers = ['Tiny Kong', 'Wario', 'Ronald R', 'Yellow Magikoopa']
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
        "Yellow Magikoopa": 30, "Ronald R": 45, "Wario": 68, "Ass Helm": 50, "Baby Peach": 30, 
        "Rocky V": 45, "Blooper": 45, "Flowery": 45, "Birdo": 69, "Mario": 58, 
        "Hunter B": 45, "Red Magikoopa": 30, "Action 52": 48, "Young Kim": 55, "Boo": 40, 
        "ChrisPratt": 45, "Shredder": 48, "Bowser Jr.": 45, "Goomba": 40, "Waluigi": 50, 
        "Wiggler": 40, "Baby Daisy": 30, "Vector": 30, "Funky Kong": 65,
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
                "DP": safe_int(row["DP"]),
                "TP": safe_int(row["TP"]),
            }
            team_list.append(player_data)

        if team in team_order_map:
            desired_order = team_order_map[team]
            team_list = sorted(team_list, key=lambda x: desired_order.index(x["name"]) if x["name"] in desired_order else 999)
        
        all_teams_data[team] = team_list

    return all_teams_data

def load_schedule_from_excel(file_path):
    df_schedule = pd.read_excel(file_path, sheet_name="Match Schedule", header=0)
    match_list = []
    for _, row in df_schedule.iterrows():
        home_team = row.iloc[1] # Column B
        away_team = row.iloc[3] # Column D
        stadium = row.iloc[4]   # Column E
        match_list.append({
            "home": home_team,
            "away": away_team,
            "stadium": stadium
        })
        
    return match_list

if __name__ == "__main__":

    data = generate_team_raw('stats.xlsx')

    blues = Team("Blues", data["Water Blues"], blues_pitchers)
    custoadians = Team("Custoadians", data["Evil Custoadians"], custoadians_pitchers)
    fighters = Team("Fighters", data["Sassy Freedom Fighters"], fighters_pitchers)
    top1 = Team("Top 1%", data["The Top 1%"], top1_pitchers)
    gasters = Team("Gasters", data["Goodraian Gasters"], gasters_pitchers)
    team = Team("Team", data["The Worlds Hardest Team"], wht_pitchers)
    miis = Team("Miis", data["Despicable Miis"], miis_pitchers)
    koopas = Team("Koopas", data["Teenage Mutant Ninja Koopas"], koopas_pitchers)
    actions = Team("Actions", data["Cheetahmen Actions"], actions_pitchers)
    emails = Team("Emails", data["Deep State Deleted Emails"], emails_pitchers)

    sim = MonteCarloSimulation(team_home=top1, team_away=fighters, stadium_name="Wario_City_Night", save_cache=True, cache_filename="pickles/top1-fighters-matchup.pkl")
    results = sim.run(trials=20000)

    sim.print_summary(results)
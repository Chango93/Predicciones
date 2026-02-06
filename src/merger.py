import json
import difflib

def normalize_name(name):
    """Normalize team names for matching (e.g. 'Club America' -> 'CF America')."""
    name = name.lower().strip()
    replacements = {
        "club america": "cf america",
        "america": "cf america",
        "chivas": "cd guadalajara",
        "guadalajara": "cd guadalajara",
        "tigres uanl": "tigres",
        "uanl": "tigres",
        "pumas unam": "pumas",
        "unam": "pumas",
        "atl. san luis": "atletico de san luis",
        "san luis": "atletico de san luis",
        "mazatlan fc": "mazatlan",
        "querétaro": "queretaro fc",
        "queretaro": "queretaro fc",
        "juárez": "fc juarez",
        "juarez": "fc juarez",
        "león": "leon"
    }
    return replacements.get(name, name)

def fuzzy_match_team(team_name, valid_teams):
    """Find the best match for a team name in a list of valid teams."""
    norm_name = normalize_name(team_name)
    best_match = None
    best_score = 0
    
    for valid in valid_teams:
        norm_valid = normalize_name(valid)
        if norm_name == norm_valid:
            return valid
        
        score = difflib.SequenceMatcher(None, norm_name, norm_valid).ratio()
        if score > best_score:
            best_score = score
            best_match = valid
            
    return best_match if best_score > 0.6 else None

def main():
    # 1. Load User Qualitative Data
    try:
        with open("data/raw/jornada 5.json", "r", encoding="utf-8") as f:
            user_data = json.load(f)
    except FileNotFoundError:
        print("Error: data/raw/jornada 5.json not found. Make sure user notes are saved there.")
        exit(1)

    # 2. Load API Quantitative Data
    try:
        with open("data/processed/jornada_5_api.json", "r", encoding="utf-8") as f:
            api_data_wrapper = json.load(f)
            api_matches = api_data_wrapper.get("matches", [])
    except FileNotFoundError:
        print("Error: data/processed/jornada_5_api.json not found.")
        print("Make sure to run fetcher.py first (or let ejecutar_predicciones.py run it).")
        exit(1)

    # 3. Define Verified Stats (From Summary) - Apertura 2025 Regular (17 Games)
    verified_apertura_stats = {
        "Toluca": {"GF": 43, "GC": 18, "PJ": 17},
        "Tigres": {"GF": 35, "GC": 16, "PJ": 17},
        "Cruz Azul": {"GF": 32, "GC": 20, "PJ": 17},
        "CF America": {"GF": 33, "GC": 18, "PJ": 17},
        "Monterrey": {"GF": 33, "GC": 29, "PJ": 17},
        "CD Guadalajara": {"GF": 29, "GC": 22, "PJ": 17},
        "Tijuana": {"GF": 29, "GC": 23, "PJ": 17},
        "FC Juarez": {"GF": 27, "GC": 28, "PJ": 17},
        "Pachuca": {"GF": 21, "GC": 21, "PJ": 17},
        "Pumas": {"GF": 24, "GC": 25, "PJ": 17},
        "Santos Laguna": {"GF": 22, "GC": 28, "PJ": 17},
        "Queretaro FC": {"GF": 19, "GC": 29, "PJ": 17},
        "Necaxa": {"GF": 24, "GC": 32, "PJ": 17},
        "Atlas": {"GF": 24, "GC": 35, "PJ": 17},
        "Atletico de San Luis": {"GF": 25, "GC": 29, "PJ": 17},
        "Mazatln": {"GF": 20, "GC": 29, "PJ": 17},
        "Mazatlan": {"GF": 20, "GC": 29, "PJ": 17},
        "Len": {"GF": 14, "GC": 31, "PJ": 17},
        "Leon": {"GF": 14, "GC": 31, "PJ": 17},
        "Puebla": {"GF": 21, "GC": 42, "PJ": 17}
    }

    # 4. Merge Logic
    merged_matches = []
    
    # Process User Matches
    for u_match in user_data:
        # User format: "Home vs Away"
        match_id = u_match.get("match_id", "")
        if " vs " in match_id:
            u_home, u_away = match_id.split(" vs ")
        else:
            continue
            
        # Find corresponding API match
        api_match_found = None
        
        # Valid team names from API to help matching
        api_teams = set()
        for am in api_matches:
            api_teams.add(am["match"]["home"])
            api_teams.add(am["match"]["away"])
            
        matched_home = fuzzy_match_team(u_home, api_teams)
        matched_away = fuzzy_match_team(u_away, api_teams)
        
        if matched_home and matched_away:
            for am in api_matches:
                if am["match"]["home"] == matched_home and am["match"]["away"] == matched_away:
                    api_match_found = am
                    break
        
        if not api_match_found:
            print(f"Warning: Could not match user match '{match_id}' to API data. Skipping.")
            continue
            
        # Start with API data (Structure & Quant Stats)
        final_entry = api_match_found.copy()
        
        # Inject User Qualitative Data
        final_entry["absences"] = u_match.get("absences", {})
        final_entry["roster_changes"] = u_match.get("roster_changes", {})
        final_entry["competitive_context"] = u_match.get("competitive_context", [])
        final_entry["pitch_notes"] = u_match.get("pitch_notes", "")
        
        # FIX: Inject Verified Historical Stats (Apertura 2025)
        # Because fetch_jornada_api.py seems to have failed to fetch history properly (GF:0)
        home_team_api = final_entry["match"]["home"]
        away_team_api = final_entry["match"]["away"]
        
        # Fix Home History
        stat_h = verified_apertura_stats.get(home_team_api)
        if not stat_h:
            # Try fuzzy match against keys
             match_key = fuzzy_match_team(home_team_api, verified_apertura_stats.keys())
             if match_key: stat_h = verified_apertura_stats[match_key]
             
        if stat_h:
            final_entry["stats"]["home"]["apertura_2025"] = stat_h
        else:
            print(f"Warning: No verified Apertura stats for {home_team_api}")

        # Fix Away History
        stat_a = verified_apertura_stats.get(away_team_api)
        if not stat_a:
             match_key = fuzzy_match_team(away_team_api, verified_apertura_stats.keys())
             if match_key: stat_a = verified_apertura_stats[match_key]

        if stat_a:
            final_entry["stats"]["away"]["apertura_2025"] = stat_a
        else:
             print(f"Warning: No verified Apertura stats for {away_team_api}")

        merged_matches.append(final_entry)

    # 5. Output
    output_wrapper = api_data_wrapper.copy()
    output_wrapper["matches"] = merged_matches
    
    output_filename = "data/processed/jornada_5_final.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(output_wrapper, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully merged {len(merged_matches)} matches into {output_filename}")

if __name__ == "__main__":
    main()

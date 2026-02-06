import argparse
import json
import requests
import datetime
import os
import sys
import time

# Constants
API_KEY = "180725"
LEAGUE_ID = "4350"
DEFAULT_SEASON = "2025-2026"
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"
CACHE_FILE = "event_stats_cache.json"

# DOM Score Configuration
DOM_MIN_MATCHES = 3  # Minimum matches with detailed stats to use DOM
DOM_MAX_AGE_DAYS = 60  # Only use stats from matches in last N days

class StatsCache:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load()
        self.modified = False

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def get(self, event_id):
        return self.data.get(str(event_id))

    def set(self, event_id, stats):
        self.data[str(event_id)] = stats
        self.modified = True

    def save(self):
        if self.modified:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)

def fetch_data(url):
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 429:
                print(f"   [429] Rate limited. Sleeping 2s... (Attempt {attempt+1}/{retries})")
                time.sleep(2)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            return {}
    return {}

def get_season_events(season):
    url = f"{BASE_URL}/eventsseason.php?id={LEAGUE_ID}&s={season}"
    data = fetch_data(url)
    return data.get("events", [])

def fetch_event_statistics(event_id, cache):
    # Check cache first
    cached = cache.get(event_id)
    if cached is not None:
        return cached

    # Fetch from API
    url = f"{BASE_URL}/lookupeventstats.php?id={event_id}"
    print(f"   -> Fetching stats for event {event_id}...")
    time.sleep(0.6) # Rate limit protection
    data = fetch_data(url)
    
    # Process stats into a clean dict
    stats_map = {}
    raw_list = data.get("eventstats")
    
    if raw_list:
        for item in raw_list:
            stat_name = item.get("strStat")
            try:
                val_h = int(item.get("intHome", 0)) if item.get("intHome") else 0
                val_a = int(item.get("intAway", 0)) if item.get("intAway") else 0
                stats_map[stat_name] = {"home": val_h, "away": val_a}
            except:
                continue
    
    # Save to cache (even if empty, to avoid re-fetching 404s constantly? 
    # Maybe store empty dict to signify 'checked but no data')
    cache.set(event_id, stats_map)
    return stats_map

def calculate_dom_proxy(gf, gc, pj):
    """
    Proxy DOM Score when detailed stats aren't available.
    Uses goal differential as a rough indicator of dominance.
    
    Logic:
    - High GF/match → likely creating chances (proxy for shots)
    - Low GC/match → likely controlling games (proxy for possession)
    - Ratio GF/GC → overall dominance
    
    Formula calibrated to match real DOM scale (2-7, avg ~4.5)
    """
    import math
    
    if pj == 0:
        return 0.0
    
    try:
        gf_per_match = gf / pj
        gc_per_match = gc / pj
        
        # Base score (league average)
        base = 4.5
        
        # Liga MX average: ~1.4 goals per match
        LIGA_AVG = 1.4
        
        # Offensive component: +/- 1.2 per goal above/below average
        offensive = 1.2 * (gf_per_match - LIGA_AVG)
        
        # Defensive component: +/- 0.8 per goal below/above average
        defensive = 0.8 * (LIGA_AVG - gc_per_match)
        
        # Ratio component: logarithmic bonus/penalty for dominance
        # Ensures strong teams (GF>>GC) get boost, weak teams (GC>>GF) get penalty
        if gf_per_match > 0.1 and gc_per_match > 0.1:
            ratio = 0.4 * math.log(gf_per_match / gc_per_match)
        else:
            ratio = 0.0
        
        dom_proxy = base + offensive + defensive + ratio
        
        # Clamp to reasonable range [1.5, 7.5]
        return max(1.5, min(7.5, dom_proxy))
    except:
        return 4.5  # Return average if calculation fails

def calculate_dom_score(stats):
    """
    Formula: 0.45*SOG + 0.20*Shots + 0.15*Corners + 0.10*(Poss-50)/10 + 0.10*(PassAcc-75)/10
    We need:
    - Shots on Goal
    - Total Shots
    - Corner Kicks
    - Ball Possession
    - Passes % (Pass Accuracy)
    """
    try:
        # Helper to get value for a side safely
        def get_val(key, side):
            return stats.get(key, {}).get(side, 0)
        
        # Calculate for HOME
        sog_h = get_val("Shots on Goal", "home")
        shots_h = get_val("Total Shots", "home")
        corn_h = get_val("Corner Kicks", "home")
        # Possession often string "50%" or int 50? API usually returns string "50" or just int. 
        # Inspect script showed int.
        poss_h = get_val("Ball Possession", "home") # Assuming 0-100 scale
        pass_acc_h = get_val("Passes %", "home")    # Assuming 0-100 scale
        
        # Normalize Possession and PassAcc logic as per formula
        # 0.10 * (Poss - 50) / 10  ==> 0.01 * (Poss - 50)
        term_poss_h = 0.01 * (poss_h - 50)
        term_pass_h = 0.01 * (pass_acc_h - 75)
        
        dom_h = (0.45 * sog_h) + (0.20 * shots_h) + (0.15 * corn_h) + term_poss_h + term_pass_h
        
        # Calculate for AWAY
        sog_a = get_val("Shots on Goal", "away")
        shots_a = get_val("Total Shots", "away")
        corn_a = get_val("Corner Kicks", "away")
        poss_a = get_val("Ball Possession", "away")
        pass_acc_a = get_val("Passes %", "away")
        
        term_poss_a = 0.01 * (poss_a - 50)
        term_pass_a = 0.01 * (pass_acc_a - 75)
        
        dom_a = (0.45 * sog_a) + (0.20 * shots_a) + (0.15 * corn_a) + term_poss_a + term_pass_a
        
        return dom_h, dom_a, True # True = Valid calculation
    except Exception as e:
        # Missing critical stats or error
        return 0, 0, False

def compute_standings_from_events(events, current_jornada_num, cache):
    """
    Iterates through all events. Aggregates basic scores AND advanced DOM stats.
    """
    stats_db = {} 
    
    def init_team(tid):
        if tid not in stats_db:
            stats_db[tid] = {
                "home": {"pj": 0, "gf": 0, "gc": 0, "w": 0, "d": 0, "l": 0, "dom_sum": 0.0, "dom_matches": 0},
                "away": {"pj": 0, "gf": 0, "gc": 0, "w": 0, "d": 0, "l": 0, "dom_sum": 0.0, "dom_matches": 0}
            }

    print(f"Processing {len(events)} events for stats aggregation...")
    
    for e in events:
        # Check if match is finished
        score_h = e.get("intHomeScore")
        score_a = e.get("intAwayScore")
        
        # Skip if scores are missing (future match)
        if score_h is None or score_a is None:
            continue
            
        try:
            val_h = int(score_h)
            val_a = int(score_a)
        except ValueError:
            continue 

        if e.get("strPostponed") == "yes":
            continue

        home_id = e.get("idHomeTeam")
        away_id = e.get("idAwayTeam")
        event_id = e.get("idEvent")
        
        if not home_id or not away_id:
            continue

        init_team(home_id)
        init_team(away_id)
        
        # --- Advanced Stats ---
        # Check if match is recent enough (within DOM_MAX_AGE_DAYS)
        from datetime import datetime, timedelta
        event_date_str = e.get("dateEvent")
        is_recent = False
        if event_date_str:
            try:
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
                days_ago = (datetime.now() - event_date).days
                is_recent = days_ago <= DOM_MAX_AGE_DAYS
            except:
                pass
        
        # Only fetch detailed stats for recent matches
        if is_recent:
            match_stats = fetch_event_statistics(event_id, cache)
            dom_h, dom_a, dom_valid = calculate_dom_score(match_stats)
        else:
            dom_h, dom_a, dom_valid = 0, 0, False
        
        # Update basic stats for Home Team
        stats_db[home_id]["home"]["pj"] += 1
        stats_db[home_id]["home"]["gf"] += val_h
        stats_db[home_id]["home"]["gc"] += val_a
        
        # Update basic stats for Away Team
        stats_db[away_id]["away"]["pj"] += 1
        stats_db[away_id]["away"]["gf"] += val_a
        stats_db[away_id]["away"]["gc"] += val_h
        
        # If detailed stats available, accumulate real DOM
        if dom_valid and not (dom_h == 0 and dom_a == 0):
            stats_db[home_id]["home"]["dom_sum"] += dom_h
            stats_db[home_id]["home"]["dom_matches"] += 1
            stats_db[away_id]["away"]["dom_sum"] += dom_a
            stats_db[away_id]["away"]["dom_matches"] += 1
        # Otherwise, proxy DOM will be calculated later from accumulated GF/GC
        
        # Update W/D/L for Home
        if val_h > val_a:
            stats_db[home_id]["home"]["w"] += 1
        elif val_h == val_a:
            stats_db[home_id]["home"]["d"] += 1
        else:
            stats_db[home_id]["home"]["l"] += 1

        # Update Away Team (Side='away')
        stats_db[away_id]["away"]["pj"] += 1
        stats_db[away_id]["away"]["gf"] += val_a
        stats_db[away_id]["away"]["gc"] += val_h
        
        if dom_valid:
            stats_db[away_id]["away"]["dom_sum"] += dom_a
            stats_db[away_id]["away"]["dom_matches"] += 1
        
        if val_a > val_h:
            stats_db[away_id]["away"]["w"] += 1
        elif val_a == val_h:
            stats_db[away_id]["away"]["d"] += 1
        else:
            stats_db[away_id]["away"]["l"] += 1

    return stats_db

def main():
    parser = argparse.ArgumentParser(description="Fetch Liga MX data from TheSportsDB")
    parser.add_argument("--jornada", type=int, required=True, help="Jornada number (e.g., 5)")
    parser.add_argument("--season", type=str, default=DEFAULT_SEASON, help="Season string (e.g., '2025-2026')")
    parser.add_argument("--output", type=str, help="Output file path (optional)")
    
    args = parser.parse_args()
    
    jornada_str = str(args.jornada)
    print(f"Fetching data for Jornada {jornada_str}, Season {args.season}...")

    # Initialize Cache
    cache = StatsCache(CACHE_FILE)

    # 1. Fetch Schedule (All events)
    events = get_season_events(args.season)
    if not events:
        print("No events found for this season.")
        return

    # Filter by Jornada for the OUTPUT list
    target_matches = [e for e in events if e.get("intRound") == jornada_str]
    
    if not target_matches:
        print(f"No matches found for Round {jornada_str}.")
        return
        
    print(f"Found {len(target_matches)} matches for Jornada {jornada_str}.")

    # 2. Compute Standings Manually (with Advanced Stats)
    print("Computing standings from match history (fetching detailed stats if needed)...")
    stats_map = compute_standings_from_events(events, args.jornada, cache)
    
    # Save cache after processing
    cache.save()
    
    # 3. Build JSON Structure
    matches_output = []
    
    for event in target_matches:
        home_id = event.get("idHomeTeam")
        away_id = event.get("idAwayTeam")
        
        home_team_name = event.get("strHomeTeam")
        away_team_name = event.get("strAwayTeam")
        
        # Determine Timestamps
        date_event = event.get("dateEvent", "")
        time_event = event.get("strTime", "00:00:00")
        kickoff = f"{date_event}T{time_event}"
        
        # Get Stats from Map (or default to 0s)
        h_stats_raw = stats_map.get(home_id, {"home": {"pj":0,"gf":0,"gc":0,"dom_sum":0,"dom_matches":0}, "away": {"pj":0,"gf":0,"gc":0,"dom_sum":0,"dom_matches":0}})
        a_stats_raw = stats_map.get(away_id, {"home": {"pj":0,"gf":0,"gc":0,"dom_sum":0,"dom_matches":0}, "away": {"pj":0,"gf":0,"gc":0,"dom_sum":0,"dom_matches":0}})
        
        # Helper to calc avg dom
        def get_avg_dom(raw_stats, side):
            matches = raw_stats[side]["dom_matches"]
            # Only use real DOM if we have minimum required matches
            if matches >= DOM_MIN_MATCHES:
                # Use real DOM average from detailed stats
                return round(raw_stats[side]["dom_sum"] / matches, 2)
            else:
                # Not enough recent data - return 0 (no DOM adjustment)
                # Previously used proxy, but decided to disable until more data available
                return 0.0

        # Build Stats Objects
        home_team_stats = {
            "clausura_2026": {
                "GF_home": h_stats_raw["home"]["gf"],
                "GC_home": h_stats_raw["home"]["gc"],
                "PJ_home": h_stats_raw["home"]["pj"],
                "GF_away": h_stats_raw["away"]["gf"],
                "GC_away": h_stats_raw["away"]["gc"],
                "PJ_away": h_stats_raw["away"]["pj"],
                
                "PJ_total": h_stats_raw["home"]["pj"] + h_stats_raw["away"]["pj"],
                "GF_total": h_stats_raw["home"]["gf"] + h_stats_raw["away"]["gf"],
                "GC_total": h_stats_raw["home"]["gc"] + h_stats_raw["away"]["gc"],
                
                # New Advanced Data
                "DOM_avg_home": get_avg_dom(h_stats_raw, "home"),
                "DOM_avg_away": get_avg_dom(h_stats_raw, "away"),
                
                "source": {
                    "evidence_level": "stats_db_top",
                    "source_url": "TheSportsDB API (Computed)",
                    "source_date": datetime.date.today().isoformat()
                },
                "derivation": {
                    "method": "computed_from_events",
                    "notes": "Calculated by aggregating all season match results with Advanced Stats (DOM)",
                    "source_urls": [f"{BASE_URL}/eventsseason.php?id={LEAGUE_ID}&s={args.season}"]
                }
            },
            "apertura_2025": { "PJ": 17, "GF": 0, "GC": 0, "source": {}, "derivation": {} }
        }

        away_team_stats = {
            "clausura_2026": {
                "GF_home": a_stats_raw["home"]["gf"],
                "GC_home": a_stats_raw["home"]["gc"],
                "PJ_home": a_stats_raw["home"]["pj"],
                "GF_away": a_stats_raw["away"]["gf"],
                "GC_away": a_stats_raw["away"]["gc"],
                "PJ_away": a_stats_raw["away"]["pj"],
                
                "PJ_total": a_stats_raw["home"]["pj"] + a_stats_raw["away"]["pj"],
                "GF_total": a_stats_raw["home"]["gf"] + a_stats_raw["away"]["gf"],
                "GC_total": a_stats_raw["home"]["gc"] + a_stats_raw["away"]["gc"],
                
                # New Advanced Data
                "DOM_avg_home": get_avg_dom(a_stats_raw, "home"),
                "DOM_avg_away": get_avg_dom(a_stats_raw, "away"),
                
                "source": {
                    "evidence_level": "stats_db_top",
                    "source_url": "TheSportsDB API (Computed)",
                    "source_date": datetime.date.today().isoformat()
                },
                "derivation": {
                    "method": "computed_from_events",
                    "notes": "Calculated by aggregating all season match results with Advanced Stats (DOM)",
                    "source_urls": [f"{BASE_URL}/eventsseason.php?id={LEAGUE_ID}&s={args.season}"]
                }
            },
            "apertura_2025": { "PJ": 17, "GF": 0, "GC": 0, "source": {}, "derivation": {} }
        }

        match_obj = {
            "match": {
                "home": home_team_name,
                "away": away_team_name,
                "jornada": f"Clausura 2026 - J{args.jornada}",
                "kickoff_datetime": kickoff,
                "cutoff_datetime": datetime.datetime.now().isoformat()
            },
            "stats": {
                "home": home_team_stats,
                "away": away_team_stats
            },
            "squad_status": { "home_squad_confirmed": False, "away_squad_confirmed": False, "notes": None },
            "absences": {"home": [], "away": []},
            "roster_changes": {"home": [], "away": []},
            "competitive_context": [],
            "venue": {
                "stadium": event.get("strVenue", "Unknown"),
                "city": event.get("strCity", event.get("strCountry", "Mexico")),
                "pitch_type": "no_confirmado",
                "evidence_level": "stats_db_top",
                "source_title": "TheSportsDB Schedule",
                "source_date": datetime.date.today().isoformat(),
                "source_url": f"{BASE_URL}/eventsseason.php?id={LEAGUE_ID}&s={args.season}"
            },
            "uncertainty": { "items": [], "hard_missing_critical": [], "hard_missing_optional": [] }
        }
        matches_output.append(match_obj)
    
    season_name = f"Clausura {args.season.split('-')[1]}" if "-" in args.season else args.season
    
    output_json = {
        "meta": {
            "season": season_name,
            "jornada_detected": f"Clausura 2026 - J{args.jornada}",
            "cutoff_datetime": datetime.datetime.now().isoformat(),
            "total_matches_in_jornada": len(matches_output),
        },
        "matches": matches_output
    }
    
    # Save
    output_path = args.output if args.output else f"jornada_{args.jornada}_api.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully generated {output_path} with {len(matches_output)} matches.")

if __name__ == "__main__":
    main()

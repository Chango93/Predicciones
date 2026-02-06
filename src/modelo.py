import json
import math
import re
import hashlib
import argparse
import random
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

# --- Constants ---
LEAGUE_AVG_HOME_G = 1.81
LEAGUE_AVG_AWAY_G = 1.29
LEAGUE_AVG_GLOBAL = (LEAGUE_AVG_HOME_G + LEAGUE_AVG_AWAY_G) / 2
DEFAULT_RHO = -0.13  # Standard Dixon-Coles correlation parameter

# Roster Adjustment Configuration
# 1. Penalties (Absences & Transfers OUT)
# (Role, Importance) -> (Target Team Lambda Multiplier, Log Message)
ROSTER_PENALTIES = {
    # FIX 2: Adjusted percentages for better calibration at PJ=4
    ("portero", "alta"):       ("OPP", 1.15, "Aumento Lambda Rival (15%) por baja Portero Titular"),  # Was 1.20
    ("portero", "media"):      ("OPP", 1.08, "Aumento Lambda Rival (8%) por baja Portero Rotación"),  # Was 1.10
    
    ("defensor", "alta"):      ("OPP", 1.12, "Aumento Lambda Rival (12%) por baja Defensor Lider"),   # Was 1.15
    ("defensor", "media"):     ("OPP", 1.06, "Aumento Lambda Rival (6%) por baja Defensor"),          # Was 1.07
    
    ("mediocampista", "alta"): ("SELF", 0.90, "Reducción Lambda Propio (10%) por baja Creativo Top"),
    ("mediocampista", "media"):("SELF", 0.95, "Reducción Lambda Propio (5%) por baja Mediocampista"),
    
    ("atacante", "alta"):      ("SELF", 0.88, "Reducción Lambda Propio (12%) por baja Goleador Top"),  # Was 0.85
    ("atacante", "media"):     ("SELF", 0.91, "Reducción Lambda Propio (9%) por baja Atacante"),       # Was 0.92
}

# Normalize role names from JSON to canonical names
ROLE_NORMALIZATION = {
    "defensa": "defensor",
    "defensa central": "defensor",
    "lateral": "defensor",
    "lateral izquierdo": "defensor",
    "lateral derecho": "defensor",
    "delantero": "atacante",
    "delantero/capitán": "atacante",
    "extremo": "atacante",
    "mediocampo": "mediocampista",
    "medio": "mediocampista",
    "central": "mediocampista",
    "arquero": "portero",
}

# 2. Boosts (Transfers IN - New Signings)
# Conservative boosts as adaptation takes time.
TRANSFER_BOOSTS = {
    ("portero", "alta"):       ("SELF", 1.03, "Mejora Lambda Propio (3%) por Fichaje Portero Top"),
    ("defensor", "alta"):      ("SELF", 1.03, "Mejora Lambda Propio (3%) por Fichaje Defensor Top"),
    ("mediocampista", "alta"): ("SELF", 1.04, "Mejora Lambda Propio (4%) por Fichaje Creativo Top"),
    ("atacante", "alta"):      ("SELF", 1.05, "Mejora Lambda Propio (5%) por Fichaje Goleador Top"),
    
    ("portero", "media"):      ("SELF", 1.01, "Mejora Lambda Propio (1%) por Fichaje Portero"),
    ("defensor", "media"):     ("SELF", 1.01, "Mejora Lambda Propio (1%) por Fichaje Defensor"),
    ("mediocampista", "media"):("SELF", 1.02, "Mejora Lambda Propio (2%) por Fichaje Medio"),
    ("atacante", "media"):     ("SELF", 1.02, "Mejora Lambda Propio (2%) por Fichaje Atacante"),
}
# 3. Contextual Adjustments (FIX 5: Less aggressive multipliers)
# "type" -> (Role "SELF" or "OPP", Lambda Multiplier, Log Message Base)
CONTEXT_ADJUSTMENTS = {
    "concacaf_load":    ("SELF", 0.95, "Reducción por Fatiga/Rotación (Concacaf)"),
    "crisis_squad":     ("SELF", 0.92, "Penalización por Crisis de Plantel/Vestidor"),  # Was 0.88
    "pressure":         ("SELF", 0.98, "Ligera Penalización por Presión/Entorno"),       # Was 0.97
    "extreme_pressure": ("SELF", 0.96, "Penalización por Presión Extrema/Técnico"),     # Was 0.94
    "momentum":         ("SELF", 1.03, "Boost por Buen Momento/Inercia Ganadora"),
    "defensive_crisis": ("OPP",  1.06, "Ventaja al Rival por Crisis Defensiva"),
    "offensive_drought":("SELF", 0.95, "Penalización por Sequía Goleadora"),
    "title_match":      ("SELF", 1.02, "Ligero Boost por Motivación (Partido Título/Clásico)"),
    "franchise_end":    ("SELF", 0.97, "Penalización por Inestabilidad (Fin Franquicia)")
}

# --- Key Players Database (SofaScore Top 100) ---
# Loaded at module init to auto-determine player importance
KEY_PLAYERS_DB = {}
ELITE_TRAITS_DB = {}  # Players with elite traits -> auto "alta" importance

def load_key_players():
    """Load key players database from JSON file."""
    global KEY_PLAYERS_DB, ELITE_TRAITS_DB
    import os
    
    # FIX 3: Check multiple candidate paths
    base = os.path.dirname(__file__)
    candidates = [
        os.path.join(base, "data", "key_players.json"),        # if modelo.py is in root
        os.path.join(base, "..", "data", "key_players.json"),  # if modelo.py is in src/
    ]
    db_path = next((p for p in candidates if os.path.exists(p)), None)
    
    if not db_path:
        print("[!] Key players database not found, using manual importance only")
        return
    
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            # Load regular players
            for player in data.get("players", []):
                name_key = player["name"].lower()
                KEY_PLAYERS_DB[name_key] = player
            
            # Load elite traits (for importance boost)
            traits_data = data.get("elite_traits_players", {})
            for trait_name, players in traits_data.items():
                for p in players:
                    name_key = p["name"].lower()
                    if name_key not in ELITE_TRAITS_DB:
                        ELITE_TRAITS_DB[name_key] = []
                    ELITE_TRAITS_DB[name_key].append(trait_name)
            
        print(f"[*] Loaded {len(KEY_PLAYERS_DB)} key players, {len(ELITE_TRAITS_DB)} with elite traits | path={db_path}")
    except Exception as e:
        print(f"[!] Error loading key players: {e}")

def get_player_importance(player_name: str, team_name: str = None) -> tuple:
    """
    Look up player importance from SofaScore database.
    Returns: (importance, role, rating, traits) or (None, None, None, None) if not found.
    
    Importance rules:
      - Has elite_trait -> "alta" (always)
      - rating >= 7.20 (Top 40) -> "alta"
      - rating >= 7.00 (Top 80) -> "media"
      - rating < 7.00 -> "baja" (not in top 80)
    """
    if not KEY_PLAYERS_DB:
        return None, None, None, None
    
    name_key = player_name.lower()
    
    # Check elite traits first (overrides rating-based importance)
    traits = ELITE_TRAITS_DB.get(name_key, [])
    
    # Direct match
    if name_key in KEY_PLAYERS_DB:
        p = KEY_PLAYERS_DB[name_key]
        if team_name and team_name.lower() not in p["team"].lower():
            return None, None, None, None
        
        rating = p["rating"]
        role = p["role"]
        
        # Elite trait = always alta
        if traits:
            importance = "alta"
        elif rating >= 7.20:
            importance = "alta"
        elif rating >= 7.00:
            importance = "media"
        else:
            importance = "baja"
        
        return importance, role, rating, traits
    
    # Fuzzy match (partial name)
    for key, p in KEY_PLAYERS_DB.items():
        if name_key in key or key in name_key:
            if team_name and team_name.lower() not in p["team"].lower():
                continue
            rating = p["rating"]
            role = p["role"]
            fuzzy_traits = ELITE_TRAITS_DB.get(key, [])
            
            if fuzzy_traits:
                importance = "alta"
            elif rating >= 7.20:
                importance = "alta"
            elif rating >= 7.00:
                importance = "media"
            else:
                importance = "baja"
            return importance, role, rating, fuzzy_traits
    
    return None, None, None, None

# Load database at module init
load_key_players()

# --- Data Structures & Validation ---

@dataclass
class TeamStats:
    name: str
    gf_curr_home: float
    gc_curr_home: float
    pj_curr_home: int
    gf_curr_away: float
    gc_curr_away: float
    pj_curr_away: int
    
    # Historical (Apertura 2025 - Regular Phase)
    gf_prior: int
    gc_prior: int
    pj_prior: int = 17
    
    # Advanced Stats (DOM Score)
    dom_avg_home: float = 0.0
    dom_avg_away: float = 0.0
    
    # xG Stats (from FBref) - Optional, used if > 0
    xg_per_match: float = 0.0    # Expected Goals per match
    xga_per_match: float = 0.0   # Expected Goals Against per match

    def total_pj_curr(self) -> int:
        return self.pj_curr_home + self.pj_curr_away


@dataclass
class Absence:
    name: str
    role: str
    importance: str
    affects_match: str # "true" (strict requirement for model impact)
    evidence_level: str

# --- Core Logic ---

def get_deterministic_seed(home: str, away: str, jornada: str) -> int:
    """
    Generates a deterministic seed based on match metadata.
    Rule: seed = int(md5((home + " vs " + away + " | " + jornada).encode("utf-8")).hexdigest()[:8], 16)
    """
    raw_str = f"{home} vs {away} | {jornada}"
    return int(hashlib.md5(raw_str.encode("utf-8")).hexdigest()[:8], 16)

def get_jornada_number(jornada_str: str) -> int:
    """Extracts numeric jornada from string like 'Clausura 2026 - J4' or returns 99 if fail."""
    try:
        # Expected format: "Word Year - J<Num>" or just number
        match = re.search(r'J(\d+)', jornada_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
        # Try raw number
        if jornada_str.isdigit():
            return int(jornada_str)
        return 99
    except Exception:
        return 99

def validate_input(data: Dict[str, Any], force: bool = False) -> None:
    """
    Validates input JSON according to strict rules.
    Raises ValueError if critical data (hard_missing_critical) is present,
    UNLESS force is True (returns warnings instead).
    """
    matches = data.get("matches", [])
    if not matches:
        raise ValueError("CRITICAL: No matches found in input.")

    for m in matches:
        # 1. Check strict hard missing
        uncertainty = m.get("uncertainty", {})
        hm_val = uncertainty.get("hard_missing_critical")
        
        # Normalize to list
        hard_missing_list = []
        if isinstance(hm_val, list):
            hard_missing_list = hm_val
        elif isinstance(hm_val, bool) and hm_val:
            # Legacy boolean True
            hard_missing_list = ["legacy_boolean_flag"]

        if hard_missing_list:
             msg = f"CRITICAL: Hard missing data flags found: {hard_missing_list}"
             if force:
                 print(f"WARNING (FORCE MODE): {msg}. Proceeding with potential garbage data.")
             else:
                 raise ValueError(msg)

        stats = m.get("stats", {})
        required_sides = ["home", "away"]
        
        for side in required_sides:
            s = stats.get(side, {})
            clausura = s.get("clausura_2026", {})
            apertura = s.get("apertura_2025", {})
            
            # Check prior season exist and PJ is 17
            if not apertura or apertura.get("PJ") != 17:
                 raise ValueError(f"CRITICAL: Invalid Apertura 2025 stats for {side}. PJ must be 17.")
                 
            # Check current season strict granular stats
            keys = ["GF_home", "GC_home", "PJ_home", "GF_away", "GC_away", "PJ_away"]
            if any(k not in clausura for k in keys):
                 raise ValueError(f"CRITICAL: Missing granular stats for {side} in Clausura 2026. 'Fallback' logic is disabled for safety.")
            
            # (FIX 1: Validate by key existence + PJ, not by >0)
            # "0 goals" is valid data, not missing data
            has_data = all(k in clausura for k in keys) and (clausura.get("PJ_home", 0) + clausura.get("PJ_away", 0)) >= 0
            source = clausura.get("source", {})
            if has_data and (not source or source.get("evidence_level") == "no_confirmado"):
                 # Allow if user explicitly flagged missing stats
                 if "stats_missing" not in hard_missing_list:
                     raise ValueError(f"CRITICAL: Stats found for {side} marked 'no_confirmado'. Use a valid source (official, medio_top, stats_db).")

def parse_team_stats(side_data: Dict[str, Any], name: str) -> TeamStats:
    curr = side_data["clausura_2026"]
    prev = side_data["apertura_2025"]
    
    # Granular stats usually present due to validation
    gf_h = curr.get("GF_home", 0)
    gc_h = curr.get("GC_home", 0)
    pj_h = curr.get("PJ_home", 0)
    gf_a = curr.get("GF_away", 0)
    gc_a = curr.get("GC_away", 0)
    pj_a = curr.get("PJ_away", 0)
    
    # Advanced Stats (DOM Score)
    dom_avg_h = curr.get("DOM_avg_home", 0.0)
    dom_avg_a = curr.get("DOM_avg_away", 0.0)
    
    # xG Stats (from FBref) - Optional
    xg_per_match = curr.get("xG_per_match", 0.0)
    xga_per_match = curr.get("xGA_per_match", 0.0)

    return TeamStats(
        name=name,
        gf_curr_home=float(gf_h), gc_curr_home=float(gc_h), pj_curr_home=int(pj_h),
        gf_curr_away=float(gf_a), gc_curr_away=float(gc_a), pj_curr_away=int(pj_a),
        gf_prior=prev["GF"], gc_prior=prev["GC"], pj_prior=prev["PJ"],
        dom_avg_home=float(dom_avg_h), dom_avg_away=float(dom_avg_a),
        xg_per_match=float(xg_per_match), xga_per_match=float(xga_per_match)
    )

def calculate_lambda(attack_stats: TeamStats, defense_stats: TeamStats, is_home: bool) -> Tuple[float, Dict[str, Any]]:
    """
    Calculates Lambda using Shrinkage (Weighted Average of Current & Prior) plus Advanced Stats Modifier (DOM).
    """
    
    # --- Shrinkage Weight Calculation (Fix 1) ---
    # Linear ramp up to 17 games
    total_pj_curr = attack_stats.total_pj_curr()
    w_curr = min(0.85, (total_pj_curr / 17.0) * 0.85)
    w_prior = 1.0 - w_curr
    
    # --- Attack Strength ---
    
    if is_home:
        # Home Team Attacking at Home
        # Compare to League Home Avg
        avg_gf_curr = attack_stats.gf_curr_home / max(1, attack_stats.pj_curr_home)
        atts_curr = avg_gf_curr / LEAGUE_AVG_HOME_G if LEAGUE_AVG_HOME_G > 0 else 1.0
        # Prior is global
        avg_gf_prior = attack_stats.gf_prior / attack_stats.pj_prior
        atts_prior = avg_gf_prior / LEAGUE_AVG_GLOBAL
    else:
        # Away Team Attacking Away
        # Compare to League Away Avg
        avg_gf_curr = attack_stats.gf_curr_away / max(1, attack_stats.pj_curr_away)
        atts_curr = avg_gf_curr / LEAGUE_AVG_AWAY_G if LEAGUE_AVG_AWAY_G > 0 else 1.0
        # Prior is global 
        avg_gf_prior = attack_stats.gf_prior / attack_stats.pj_prior
        atts_prior = avg_gf_prior / LEAGUE_AVG_GLOBAL
    
    atts_final_base = (atts_curr * w_curr) + (atts_prior * w_prior)
    
    # --- Advanced Stats Modifier ---
    # Priority: xG (FBref) > DOM (TheSportsDB)
    # xG is more reliable when available
    
    LEAGUE_AVG_XG = 1.55   # Liga MX average xG per match
    K_XG = 0.08            # xG has stronger predictive power
    LEAGUE_DOM_AVG = 4.5   # Fallback DOM average
    K_DOM = 0.04
    
    adv_modifier = 1.0
    adv_note = ""
    
    # Check if xG data is available (non-zero)
    if attack_stats.xg_per_match > 0.1:
        # Use xG-based modifier
        xg_diff = attack_stats.xg_per_match - LEAGUE_AVG_XG
        xg_diff_capped = max(-1.0, min(1.0, xg_diff))  # Cap at +/- 1.0 xG from average
        adv_modifier = 1.0 + (K_XG * xg_diff_capped)
        adv_note = f" (xG {attack_stats.xg_per_match:.2f}, mod {adv_modifier:.2f})"
    else:
        # Fallback to DOM if xG not available
        dom_val = attack_stats.dom_avg_home if is_home else attack_stats.dom_avg_away
        if dom_val > 0.5:
            diff = dom_val - LEAGUE_DOM_AVG
            diff_capped = max(-3.0, min(3.0, diff))
            adv_modifier = 1.0 + (K_DOM * diff_capped)
            adv_note = f" (DOM {adv_modifier:.2f})"
        
    atts_final = atts_final_base * adv_modifier

    # --- Defense Strength ---
    
    if is_home:
        # We are calculating HOME Lambda. 
        # So we need DefS of the OPPONENT (defense_stats) when they play AWAY.
        # (Fix 2: Correctly accessing gc_curr_away for the away team)
        avg_gc_curr = defense_stats.gc_curr_away / max(1, defense_stats.pj_curr_away)
        
        # Normalized against what usually happens to an Away Defense?
        # An Away Defense usually concedes LEAGUE_AVG_HOME_G.
        # So DefS = Goals Conceded / Expected Conceded (League Home G)
        defs_curr = avg_gc_curr / LEAGUE_AVG_HOME_G
        
    else:
        # We are calculating AWAY Lambda.
        # So we need DefS of the OPPONENT (defense_stats) when they play HOME.
        avg_gc_curr = defense_stats.gc_curr_home / max(1, defense_stats.pj_curr_home)
        
        # A Home Defense usually concedes LEAGUE_AVG_AWAY_G.
        defs_curr = avg_gc_curr / LEAGUE_AVG_AWAY_G

    # Prior Defense (Global)
    avg_gc_prior = defense_stats.gc_prior / defense_stats.pj_prior
    defs_prior = avg_gc_prior / LEAGUE_AVG_GLOBAL
    
    defs_final = (defs_curr * w_curr) + (defs_prior * w_prior)
    
    # --- Final Lambda Calculation ---
    expected_goals = 0.0
    if is_home:
        # Expected = AttS(Home) * DefS(Away_at_Away) * LeagueAvgHome
        expected_goals = atts_final * defs_final * LEAGUE_AVG_HOME_G
    else:
        # Expected = AttS(Away) * DefS(Home_at_Home) * LeagueAvgAway
        expected_goals = atts_final * defs_final * LEAGUE_AVG_AWAY_G
        
    final_val = max(0.1, expected_goals)
    
    # FIX 3: Separate atts_base from atts (with xG/DOM modifier)
    adv_type = "xG" if attack_stats.xg_per_match > 0.1 else "DOM"
    breakdown = {
        "atts_base": round(atts_final_base, 3),
        "atts": round(atts_final, 3),
        "defs": round(defs_final, 3),
        "w_curr": round(w_curr, 2),
        "w_prior": round(w_prior, 2),
        "league_avg": LEAGUE_AVG_HOME_G if is_home else LEAGUE_AVG_AWAY_G,
        "raw_lambda": round(final_val, 3),
        "note": f"BaseAtt:{atts_final_base:.2f}{adv_note}" if adv_note else "",
        "adv_type": adv_type
    }
        
    return final_val, breakdown

def get_w_prior(team: TeamStats) -> float:
    """Calculates the weight of prior season data."""
    total_pj = team.total_pj_curr()
    w_curr = min(0.85, (total_pj / 17.0) * 0.85)
    return 1.0 - w_curr

def apply_roster_adjustments(lambdas: Dict[str, float], match_data: Dict[str, Any], weights: Dict[str, float]) -> Tuple[Dict[str, float], List[str]]:
    absences = match_data.get("absences", {})
    roster_changes = match_data.get("roster_changes", {}) # New field for transfers
    context_items = match_data.get("competitive_context", []) # NEW
    match_meta = match_data.get("match", {})  # For team name lookups
    
    new_lambdas = lambdas.copy()
    logs = []
    
    # --- FIX 1: DEDUPE - transfer_out takes precedence over absence ---
    # If a player is in both absences AND roster_changes.transfer_out, only process transfer_out
    def norm_name(n: str) -> str:
        return re.sub(r"\s+", " ", (n or "").strip().lower())
    
    for side in ["home", "away"]:
        out_names = {norm_name(p.get("name")) for p in roster_changes.get(side, [])
                     if p.get("type") == "transfer_out"}
        
        if out_names:
            cleaned = []
            for p in absences.get(side, []):
                if norm_name(p.get("name")) in out_names:
                    print(f"    [DEDUPE] {p.get('name')} en transfer_out, ignorando absence")
                    continue
                cleaned.append(p)
            absences[side] = cleaned
    # --- END DEDUPE ---
    
    valid_sources = ["oficial_club", "liga_mx_oficial", "medio_top", "stats_db_top", "alto_confirmado", "medio_declaraciones"]
    
    # Smart Default Logic
    jornada_num = 99
    if match_data and "match" in match_data:
        jornada_num = get_jornada_number(match_data["match"].get("jornada", ""))

    # --- BLOCK-BASED MULTIPLIER CAPS ---
    # Track cumulative impact per team per block to prevent apocalyptic stacking
    context_multipliers = {}     # team -> cumulative (cap: 0.92 to 1.08 = ±8%)
    offensive_multipliers = {}   # team -> cumulative (cap: 0.75 = -25%)
    def_gk_multipliers = {}      # team -> cumulative for GK absences (cap: 1.15 = +15%)
    def_field_multipliers = {}   # team -> cumulative for defender absences (cap: 1.15 = +15%)
    
    # Cap bounds
    CONTEXT_CAP_LOWER = 0.92    # -8% max
    CONTEXT_CAP_UPPER = 1.08    # +8% max
    OFFENSIVE_CAP_LOWER = 0.75  # -25% max
    DEF_GK_CAP_UPPER = 1.15     # +15% max for GK bucket
    DEF_FIELD_CAP_UPPER = 1.15  # +15% max for DEF bucket

    def apply_effect(target_key_self, target_key_opp, effect_tuple, item_name, is_context=False, block_type=None, role_type=None):
        """
        block_type: 'offensive', 'defensive_gk', 'defensive_field', or None (for context)
        role_type: the player's role for better logging
        """
        target_role, multiplier, msg_base = effect_tuple
        
        # Determine which team is affected
        affected_team = target_key_self if target_role == "SELF" else target_key_opp
        final_mult_to_apply = multiplier
        cap_hit = False
        
        # --- Apply appropriate cap based on block type ---
        if is_context:
            # Context cap: ±8%
            curr_cum = context_multipliers.get(affected_team, 1.0)
            potential_cum = curr_cum * multiplier
            
            if potential_cum < CONTEXT_CAP_LOWER:
                clamped = CONTEXT_CAP_LOWER
                final_mult_to_apply = clamped / curr_cum if curr_cum > 0 else 1.0
                context_multipliers[affected_team] = clamped
                cap_hit = True
            elif potential_cum > CONTEXT_CAP_UPPER:
                clamped = CONTEXT_CAP_UPPER
                final_mult_to_apply = clamped / curr_cum if curr_cum > 0 else 1.0
                context_multipliers[affected_team] = clamped
                cap_hit = True
            else:
                context_multipliers[affected_team] = potential_cum
                
        elif block_type == "offensive":
            # Offensive cap: -25% max (affects SELF lambda)
            curr_cum = offensive_multipliers.get(affected_team, 1.0)
            potential_cum = curr_cum * multiplier
            
            if potential_cum < OFFENSIVE_CAP_LOWER:
                clamped = OFFENSIVE_CAP_LOWER
                final_mult_to_apply = clamped / curr_cum if curr_cum > 0 else 1.0
                offensive_multipliers[affected_team] = clamped
                cap_hit = True
            else:
                offensive_multipliers[affected_team] = potential_cum
                
        elif block_type == "defensive_gk":
            # GK bucket: +15% max (portero absences only)
            curr_cum = def_gk_multipliers.get(affected_team, 1.0)
            potential_cum = curr_cum * multiplier
            
            if potential_cum > DEF_GK_CAP_UPPER:
                clamped = DEF_GK_CAP_UPPER
                final_mult_to_apply = clamped / curr_cum if curr_cum > 0 else 1.0
                def_gk_multipliers[affected_team] = clamped
                cap_hit = True
            else:
                def_gk_multipliers[affected_team] = potential_cum
                
        elif block_type == "defensive_field":
            # DEF field bucket: +15% max (defensor absences only)
            curr_cum = def_field_multipliers.get(affected_team, 1.0)
            potential_cum = curr_cum * multiplier
            
            if potential_cum > DEF_FIELD_CAP_UPPER:
                clamped = DEF_FIELD_CAP_UPPER
                final_mult_to_apply = clamped / curr_cum if curr_cum > 0 else 1.0
                def_field_multipliers[affected_team] = clamped
                cap_hit = True
            else:
                def_field_multipliers[affected_team] = potential_cum
        
        if cap_hit:
            msg_base += " [CAP HIT]"
        
        multiplier = final_mult_to_apply
        
        # DEBUG: Store lambda BEFORE modification
        lambda_before_self = new_lambdas[target_key_self]
        lambda_before_opp = new_lambdas[target_key_opp]
        
        # Apply multiplier to appropriate lambda
        if target_role == "SELF":
            new_lambdas[target_key_self] *= multiplier
            affected_key = target_key_self
            lambda_after = new_lambdas[target_key_self]
            lambda_before = lambda_before_self
        else: # OPP
            new_lambdas[target_key_opp] *= multiplier
            affected_key = target_key_opp
            lambda_after = new_lambdas[target_key_opp]
            lambda_before = lambda_before_opp
        
        # Calculate ACTUAL impact percentage (after application)
        actual_mult = lambda_after / lambda_before if lambda_before > 0 else 1.0
        pct = (actual_mult - 1.0) * 100
        sign = "+" if pct > 0 else ""
        impact_str = f"[{sign}{pct:.1f}%]"
        
        # DEBUG: Verify multiplier matches expectation
        expected_pct = (multiplier - 1.0) * 100
        if abs(pct - expected_pct) > 0.5:  # Tolerance for rounding
            print(f"⚠️ MULTIPLIER MISMATCH: Expected {expected_pct:+.1f}%, Got {pct:+.1f}% | {affected_key} | {item_name[:50]}")
        
        # Log with side tag for reliable filtering
        side_tag = f"[{affected_key.upper()}]"
        
        # Get actual team names for clearer logs
        home_name = match_meta.get("home", "Home")
        away_name = match_meta.get("away", "Away")
        beneficiary_name = home_name if affected_key == "home" else away_name
        
        if target_role == "SELF":
            logs.append(f"{side_tag} {impact_str} {msg_base}: {item_name}")
        else: # OPP - Clarify who benefits with actual team name
            logs.append(f"{side_tag} {impact_str} {msg_base} (→ Beneficia {beneficiary_name}): {item_name}")

    def process_impact(team_key: str, opponent_key: str, team_label: str, item: Dict[str, Any]):
        # Common filter logic - allow items with valid evidence_level OR source_url
        evidence = item.get("evidence_level")
        has_source = bool(item.get("source_url"))
        if evidence and evidence not in valid_sources and not has_source: 
            return  # Only skip if explicitly has invalid evidence AND no source_url
        
        name = item.get("name", "Jugador")
        role = item.get("role")
        imp = item.get("importance")
        type_ = item.get("type", "absence") 
        
        # --- AUTO-LOOKUP FROM KEY_PLAYERS DATABASE ---
        # Check if player is elite FIRST (before affects_match check)
        team_name = match_meta.get("home") if team_key == "home" else match_meta.get("away")
        db_imp, db_role, db_rating, db_traits = get_player_importance(name, team_name)
        is_elite_player = bool(db_traits) or (db_rating and db_rating >= 7.20)
        
        # Fill role/importance from DB if not specified
        if db_imp and db_role:
            if not role:
                role = db_role
            if not imp:
                imp = db_imp
            # Log the auto-lookup
            traits_str = f", traits:{db_traits}" if db_traits else ""
            print(f"    [AUTO] {name} -> role:{role}, importance:{imp} (SofaScore {db_rating:.2f}{traits_str})")
        
        # affects_match check: 
        # - ELITE PLAYERS: Auto-apply even without affects_match
        # - Regular players: Strict only if explicit 'false'
        is_context_item = "type" in item and item.get("type") in CONTEXT_ADJUSTMENTS
        
        if not is_context_item and not is_elite_player:
            # Only skip if explicitly marked as false AND not elite
            if str(item.get("affects_match", "true")).lower() == "false": 
                return
        elif is_elite_player and str(item.get("affects_match", "")).lower() == "false":
            # Elite player with explicit false - log but still apply reduced effect
            print(f"    [ELITE-OVERRIDE] {name} marked as no-impact but elite -> applying 50% penalty")
        
        # MAPPING - Normalize role before lookup
        effect = None
        role_normalized = ROLE_NORMALIZATION.get(role.lower(), role) if role else role
        
        if type_ == "transfer_in":
            effect = TRANSFER_BOOSTS.get((role_normalized, imp))
        elif type_ in ("transfer_out", "absence"): 
            effect = ROSTER_PENALTIES.get((role_normalized, imp))
            
        if not effect: return
        
        target, base_multiplier, msg_base = effect
        
        # --- FIX 6: DUDA STATUS APPLIES 50% EFFECT ---
        # If status=="duda", apply only half the penalty/boost
        status = item.get("status", "fuera")
        if status == "duda":
            # Apply 50% of the effect: mult = 1 + (base - 1) * 0.5
            base_multiplier = 1.0 + (base_multiplier - 1.0) * 0.5
            msg_base += " (Duda: 50% efecto)"
        
        # --- DYNAMIC FADE-OUT LOGIC (HYBRID APPROACH) ---
        final_multiplier = base_multiplier
        note = ""
        
        if type_ in ("transfer_in", "transfer_out"):
            # New patch_mode: "match" (full impact) vs "blend" (faded)
            mode = item.get("patch_mode")
            if not mode:
                # Default logic: J1-J3 = match (full impact), else blend
                mode = "match" if jornada_num <= 3 else "blend"
            
            if mode == "match":
                final_multiplier = base_multiplier
                note = " (Impacto full match)"
            else:
                # FIX 2: Use w_prior for the AFFECTED team (not event team)
                # If OPP effect, the affected team is opponent
                target_role, _, _ = effect
                affected_key = team_key if target_role == "SELF" else opponent_key
                wp = weights.get(affected_key, 0.5)
                
                # HYBRID APPROACH:
                # - transfer_in: Apply adaptation factor (0.7 in J1-J3, 1.0 after)
                #   Reason: Fichajes need time to adapt (chemistry, system, minutes)
                # - transfer_out: Apply directly (no adaptation)
                #   Reason: Loss of key player impacts immediately
                
                if type_ == "transfer_in":
                    # Adaptation factor: smooth transition J1-J4
                    # J1: 0.70, J2: 0.80, J3: 0.90, J4+: 1.00
                    if jornada_num == 1:
                        adapt_factor = 0.70
                    elif jornada_num == 2:
                        adapt_factor = 0.80
                    elif jornada_num == 3:
                        adapt_factor = 0.90
                    else:
                        adapt_factor = 1.00
                    
                    # Formula: mult = 1 + (base - 1) * w_prior * adapt
                    final_multiplier = 1.0 + ((base_multiplier - 1.0) * wp * adapt_factor)
                    note = f" (Pond. Hist: {wp:.0%}, Adapt: {adapt_factor:.0%})"
                else:  # transfer_out
                    # Direct application (loss impacts immediately)
                    # Formula: mult = 1 + (base - 1) * w_prior
                    final_multiplier = 1.0 + ((base_multiplier - 1.0) * wp)
                    note = f" (Pond. Hist: {wp:.0%})"

        # Custom log message
        if type_ == "transfer_in":
             msg_base = msg_base.replace("baja", "Alta/Fichaje").replace("Mejora", "BOOST")
        elif type_ == "transfer_out":
             msg_base = msg_base.replace("baja", "BAJA/Transferencia")

        # Determine block_type for cap enforcement
        # SELF adjustments (atacante, mediocampista) = offensive cap
        # OPP adjustments = split into GK bucket (portero) and DEF bucket (defensor)
        if target == "SELF":
            block_type = "offensive"
        elif role_normalized == "portero":
            block_type = "defensive_gk"
        else:  # defensor
            block_type = "defensive_field"
        
        apply_effect(team_key, opponent_key, (target, final_multiplier, msg_base + note), name, block_type=block_type, role_type=role_normalized)

    # 1. Process Absences & Roster Changes
    for side, side_label, opp_side in [("home", "Local", "away"), ("away", "Visita", "home")]:
        # Standard Absences
        for p in absences.get(side, []):
            p["type"] = "absence"
            process_impact(side, opp_side, side_label, p)
            
        # Roster Changes (Transfers)
        for p in roster_changes.get(side, []):
            process_impact(side, opp_side, side_label, p)
            
    # 2. Process Contextual Factors
    # NEW APPROACH: Use explicit "team" field instead of parsing claim text
    # JSON structure: {"type":"pressure", "team":"home", "claim":"..."}
    
    # Build set of absence names per team for dedupe
    absence_names_by_team = {}
    for side in ["home", "away"]:
        absence_names_by_team[side] = {norm_name(p.get("name")) for p in absences.get(side, [])}
    
    for ctx in context_items:
        c_type = ctx.get("type")
        team_affected = ctx.get("team")  # "home" or "away" - EXPLICIT
        
        # Validation: team field must be "home" or "away"
        if c_type in CONTEXT_ADJUSTMENTS:
            if team_affected not in ["home", "away"]:
                # Log warning for invalid team value
                claim_text = ctx.get("claim", "")
                logs.append(f"[WARNING] Context item with invalid team='{team_affected}': {claim_text}")
                continue  # Skip this context item
            
            # --- DEDUPE: Skip defensive_crisis if the player mentioned is already in absences ---
            if c_type == "defensive_crisis":
                claim_text = ctx.get("claim", "").lower()
                # Check if any absence player name (or last name) appears in the claim
                is_duplicate = False
                for absence_name in absence_names_by_team.get(team_affected, set()):
                    if not absence_name or len(absence_name) < 3:
                        continue
                    # Check full name
                    if absence_name in claim_text:
                        print(f"    [DEDUPE-CRISIS] Skipping crisis_defensiva - player '{absence_name}' already in absences")
                        is_duplicate = True
                        break
                    # Check last name only (for cases like "Micolta" instead of "Andrés Micolta")
                    last_name = absence_name.split()[-1] if " " in absence_name else ""
                    if last_name and len(last_name) > 3 and last_name in claim_text:
                        print(f"    [DEDUPE-CRISIS] Skipping crisis_defensiva - player '{last_name}' (from {absence_name}) already in absences")
                        is_duplicate = True
                        break
                if is_duplicate:
                    continue
            
            # Determine opponent
            opp_side = "away" if team_affected == "home" else "home"
            
            effect = CONTEXT_ADJUSTMENTS[c_type]
            apply_effect(team_affected, opp_side, effect, ctx.get("claim"), is_context=True)


    return new_lambdas, logs

def dixon_coles_adjustment(p: float, x: int, y: int, lambda_h: float, lambda_a: float, rho: float) -> float:
    if x == 0 and y == 0:
        return p * (1.0 - (lambda_h * lambda_a * rho))
    elif x == 0 and y == 1:
        return p * (1.0 + (lambda_h * rho))
    elif x == 1 and y == 0:
        return p * (1.0 + (lambda_a * rho))
    elif x == 1 and y == 1:
        return p * (1.0 - rho)
    else:
        return p

def get_outcome(score_str: str) -> str:
    h, a = map(int, score_str.split("-"))
    if h > a: return "HOME"
    if a > h: return "AWAY"
    return "DRAW"

def run_simulation(data: Dict[str, Any], force_mode: bool = False) -> None:
    # (Fix 6) Loop through all matches
    validate_input(data, force_mode)
    
    all_predictions = []
    
    for match_entry in data["matches"]:
        match_meta = match_entry["match"]
        home_name = match_meta["home"]
        away_name = match_meta["away"]
        jornada = match_meta["jornada"]
        
        # Seed
        seed_val = get_deterministic_seed(home_name, away_name, jornada)
        random.seed(seed_val)
        
        # Stats Parsing
        home_stats = parse_team_stats(match_entry["stats"]["home"], home_name)
        away_stats = parse_team_stats(match_entry["stats"]["away"], away_name)
        
        # Calculate Base Lambdas
        lambda_home, bd_home = calculate_lambda(home_stats, away_stats, is_home=True)
        lambda_away, bd_away = calculate_lambda(away_stats, home_stats, is_home=False)
        
        lambdas = {"home": lambda_home, "away": lambda_away}
        
        # Weights for Transfer Fade-Out
        weights = {
            "home": get_w_prior(home_stats), 
            "away": get_w_prior(away_stats)
        }
        
        # CRITICAL: Save original lambdas BEFORE adjustments for reporting
        lambdas_original = lambdas.copy()
        
        # Adjustments (this MODIFIES lambdas dict)
        lambdas, logs = apply_roster_adjustments(lambdas, match_entry, weights)
        
        # Monte Carlo Simulation
        CALC_LIMIT = 10 
        REPORT_LIMIT = 6 
        
        matrix_probs = []
        matrix_outcomes = []
        total_prob = 0.0
        
        for x in range(CALC_LIMIT + 1):
            for y in range(CALC_LIMIT + 1):
                p_x = (math.exp(-lambdas["home"]) * (lambdas["home"] ** x)) / math.factorial(x)
                p_y = (math.exp(-lambdas["away"]) * (lambdas["away"] ** y)) / math.factorial(y)
                p_raw = p_x * p_y
                
                p_adj = dixon_coles_adjustment(p_raw, x, y, lambdas["home"], lambdas["away"], DEFAULT_RHO)
                p_adj = max(0.0, p_adj)
                
                score_str = f"{x}-{y}"
                matrix_probs.append(p_adj)
                matrix_outcomes.append(score_str)
                total_prob += p_adj
        
        # Re-normalize
        if total_prob > 0:
            matrix_probs = [p / total_prob for p in matrix_probs]
        
        # Collapse scores >6 to prevent sparse matrix
        # Build deterministic score dictionary from matrix
        score_probs = {}
        idx = 0
        for x in range(11):  # CALC_LIMIT + 1
            for y in range(11):
                x_final = min(REPORT_LIMIT, x)
                y_final = min(REPORT_LIMIT, y)
                score_str = f"{x_final}-{y_final}"
                score_probs[score_str] = score_probs.get(score_str, 0.0) + matrix_probs[idx]
                idx += 1
        
        # Sanity check: probabilities should sum to ~1.0
        total_prob = sum(score_probs.values())
        if abs(total_prob - 1.0) > 1e-6:
            print(f"WARNING: score_probs sum={total_prob:.6f}, expected 1.0")
        
        # --- Quiniela Optimization Logic (Deterministic) ---
        
        # 1. Calculate Outcome Probabilities (Home/Draw/Away) from matrix
        p_outcomes = {"HOME": 0.0, "DRAW": 0.0, "AWAY": 0.0}
        for score, prob in score_probs.items():
            outcome = get_outcome(score)
            p_outcomes[outcome] += prob
        
        # 2. Analyze Top Candidates for EV (Expected Value)
        # Rule: Exact=2pts, Trend=1pt. EV = P(Exact)*2 + P(Trend_but_not_Exact)*1
        # Simplified: EV = P(Exact) + P(Trend)
        
        # Sort scores by probability (deterministic)
        sorted_scores = sorted(score_probs.items(), key=lambda x: x[1], reverse=True)
        
        candidates = []
        for score, p_exact in sorted_scores[:8]:
            outcome_pick = get_outcome(score)
            p_trend = p_outcomes[outcome_pick]
            
            # --- FIX 4: CLEAN SHEET BONUS (Cazador de Ceros) ---
            # Strategy: Favor 1-0/2-0/0-0/0-1/0-2 over 2-1 IF justified.
            # FIXED: Now checks BOTH:
            #   1) Weak attack of team held scoreless (low lambda)
            #   2) Good defense of team keeping the clean sheet (low defs = concedes less)
            
            bonus = 0.0
            h_s, a_s = map(int, score.split("-"))
            is_clean_sheet = (h_s == 0 or a_s == 0)
            
            if is_clean_sheet:
                # For 1-0 / 2-0 etc: Home scores, Away at 0
                # Check: away attack weak (lambda) AND home defense solid (defs < 1.0)
                if a_s == 0 and h_s > 0:  # Home wins with clean sheet
                    away_attack_weak = lambdas["away"] < 0.95
                    home_def_solid = bd_away.get("defs", 1.0) < 1.0  # away's defs = how weak they are defensively
                    if away_attack_weak and home_def_solid:
                        bonus = 0.04
                    elif away_attack_weak:  # At least attack is weak
                        bonus = 0.02
                        
                # For 0-1 / 0-2 etc: Away scores, Home at 0
                elif h_s == 0 and a_s > 0:  # Away wins with clean sheet
                    home_attack_weak = lambdas["home"] < 0.95
                    away_def_solid = bd_home.get("defs", 1.0) < 1.0  # home's defs in bd_home used for away calc
                    if home_attack_weak and away_def_solid:
                        bonus = 0.04
                    elif home_attack_weak:
                        bonus = 0.02
                        
                # For 0-0: Both attacks weak
                elif h_s == 0 and a_s == 0:
                    if lambdas["home"] < 0.95 and lambdas["away"] < 0.95:
                        bonus = 0.04
                    elif lambdas["home"] < 0.95 or lambdas["away"] < 0.95:
                        bonus = 0.02
            
            ev = p_exact + p_trend + bonus
            
            candidates.append({
                "score": score,
                "p": round(p_exact, 4),
                "trend": outcome_pick,
                "p_trend": round(p_trend, 4),
                "ev": round(ev, 4),
                "bonus": bonus > 0  # Flag for logs/debug if needed
            })
            
        # Sort candidates by EV (Quiniela Strategy)
        candidates.sort(key=lambda x: x["ev"], reverse=True)
        
        best_pick = candidates[0]["score"]
        
        output = {
            "match": {
                "home": home_name,
                "away": away_name,
                "jornada": jornada
            },
            "seed": seed_val,
            "lambdas": lambdas,  # Final lambdas (after adjustments)
            "lambdas_original": lambdas_original,  # Original lambdas (before adjustments)
            "breakdown": {
                "home": bd_home,
                "away": bd_away
            },
            "correction_logs": logs,
            "outcome_probs": {k: round(v, 4) for k, v in p_outcomes.items()},
            "candidates_ev": candidates,
            "pick_final": best_pick,
            "notes": ["Optimization: Quiniela EV (P_Exact + P_Trend)"]
        }
        
        print(json.dumps(output, indent=2))
        
        # Store for report
        all_predictions.append(output)

    # Generate Markdown Report
    generate_markdown_report(all_predictions, data["matches"])

def generate_markdown_report(predictions: List[Dict[str, Any]], matches: List[Dict[str, Any]]) -> None:
    """
    Generates a Markdown report for the user.
    """
    filename = "reports/reporte_tecnico_automatico.md"
    print(f"Generating report: {filename}...")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# 🔢 Reporte Técnico: Optimización Quiniela (EV)\n\n")
        
        # --- FORCE MODE WARNING ---
        forced_errors = set()
        for m in matches:
            unc = m.get("uncertainty", {})
            hm_val = unc.get("hard_missing_critical")
            if isinstance(hm_val, list):
                for err in hm_val: forced_errors.add(err)
            elif isinstance(hm_val, bool) and hm_val:
                forced_errors.add("Critical Data Missing (Legacy Flag)")
        
        if forced_errors:
            f.write("> [!CAUTION]\n")
            f.write("> **REPORTE GENERADO EN MODO FORZADO (Datos Incompletos)**\n")
            f.write("> Este reporte se generó ignorando validaciones críticas. Los resultados pueden ser erróneos (e.g. 0-0 masivo).\n")
            f.write("> **Datos faltantes detectados:**\n")
            for err in sorted(forced_errors):
                f.write(f"> - `{err}`\n")
            f.write("\n")
        # --------------------------

        f.write(f"**Generado:** {datetime.now().isoformat()}\n")
        f.write(f"**Estrategia:** Maximizar Puntos (2pts Exacto / 1pt Resultado)\n")
        f.write(f"**Fórmula EV:** Prob. Exacta + Prob. Resultado\n\n")
        f.write("---\n\n")
        
        summary_rows = []
        
        for i, p in enumerate(predictions):
            # Link prediction to raw data (assuming same order)
            raw_match = matches[i] if i < len(matches) else {}
            
            home = p["match"]["home"]
            away = p["match"]["away"]
            l_home = p["lambdas"]["home"]
            l_away = p["lambdas"]["away"]
            
            f.write(f"## {home} vs. {away}\n")
            
            # --- NEW: Qualitative Context Section ---
            f.write("### 🗞️ Contexto y Novedades\n")
            
            has_news = False
            
            # 1. Competitive Context
            context_list = raw_match.get("competitive_context", [])
            if context_list:
                has_news = True
                for c in context_list:
                    c_type = c.get("type", "").lower()
                    emoji = "ℹ️"
                    if c_type in ["pressure", "crisis_squad"]: emoji = "🔥"
                    if c_type in ["momentum"]: emoji = "🚀"
                    if c_type in ["concacaf_load"]: emoji = "✈️"
                    # Mark items that don't affect model
                    info_tag = "" if c_type in CONTEXT_ADJUSTMENTS else " *(info, no ajusta modelo)*"
                    f.write(f"- {emoji} **{c_type.upper()}:** {c.get('claim')}{info_tag}\n")

            # 2. Key Roster Changes (Transfers)
            r_changes = raw_match.get("roster_changes", {})
            transfers_text = []
            
            for side, label in [("home", home), ("away", away)]:
                for item in r_changes.get(side, []):
                    name = item.get("name")
                    role = item.get("role")
                    type_ = item.get("type")
                    
                    # Check if player is elite
                    db_imp, db_role, db_rating, db_traits = get_player_importance(name, label)
                    
                    # Auto-fill importance from DB
                    importance = item.get("importance") or db_imp
                    if importance not in ["alta", "media"]: continue
                    
                    # Build elite indicator
                    elite_tag = ""
                    if db_traits:
                        traits_short = "/".join([t.replace("elite_", "").replace("high_", "") for t in db_traits])
                        elite_tag = f" ⭐ **ELITE**"
                    elif db_rating and db_rating >= 7.20:
                        elite_tag = f" ⭐"
                    
                    if type_ == "transfer_in":
                        transfers_text.append(f"🟢 **ALTA ({label}):**{elite_tag} {name} ({role})")
                    elif type_ == "transfer_out":
                        transfers_text.append(f"🔴 **BAJA ({label}):**{elite_tag} {name} ({role})")
            
            if transfers_text:
                has_news = True
                f.write("\n**Movimientos de Mercado:**\n")
                for t in transfers_text:
                    f.write(f"- {t}\n")

            # 3. Key Absences (Injuries/Suspensions)
            absences = raw_match.get("absences", {})
            absences_text = []
            
            for side, label in [("home", home), ("away", away)]:
                for item in absences.get(side, []):
                    if item.get("status") not in ["fuera", "duda"]: continue
                    
                    name = item.get("name")
                    reason = item.get("reason", "")
                    status = "🚑 Baja" if item.get("status") == "fuera" else "⚠️ Duda"
                    
                    # Check if player is elite
                    db_imp, db_role, db_rating, db_traits = get_player_importance(name, label)
                    
                    # Auto-filter by importance: use DB if not specified
                    importance = item.get("importance") or db_imp
                    if importance not in ["alta", "media"]: continue
                    
                    # Build elite indicator
                    elite_tag = ""
                    if db_traits:
                        traits_short = "/".join([t.replace("elite_", "").replace("high_", "") for t in db_traits])
                        elite_tag = f" ⭐ **ELITE ({traits_short})**"
                    elif db_rating and db_rating >= 7.20:
                        elite_tag = f" ⭐ Top-40 (Rating: {db_rating:.2f})"
                    
                    absences_text.append(f"{status} **({label}):** {name}{elite_tag} - *{reason}*")
            
            if absences_text:
                has_news = True
                f.write("\n**Ausencias Relevantes:**\n")
                for a in absences_text:
                    f.write(f"- {a}\n")

            if raw_match.get("pitch_notes"):
                has_news = True
                f.write(f"\n- 🏟️ *{raw_match.get('pitch_notes')}*\n")
            
            if not has_news:
                f.write("*(Sin novedades relevantes reportadas)*\n")

            f.write("\n")
            # ----------------------------------------

            # --- Lambda Analysis (Restored) ---
            bd_home = p["breakdown"]["home"]
            bd_away = p["breakdown"]["away"]
            
            f.write(f"### 🧪 Análisis de Lambdas (Goles Esperados)\n")
            
            # Detailed Breakdown for Home
            f.write(f"**{home} (Local) = {l_home:.4f}**\n")
            f.write(f"- *Fuerza Ataque*: {bd_home['atts']} (Pond: {bd_home['w_curr']} Actual + {bd_home['w_prior']} Prior)\n")
            f.write(f"- *Fuerza Defensa Rival*: {bd_home['defs']}\n")
            f.write(f"- *Media Liga Local*: {bd_home['league_avg']}\n")
            f.write(f"- *Cálculo Base*: {bd_home['atts']} * {bd_home['defs']} * {bd_home['league_avg']} = {bd_home['raw_lambda']}\n")
            if bd_home.get('note'):
                f.write(f"- ⚡ *Ajuste DOM*: {bd_home['note']}\n")

            # Detailed Breakdown for Away
            f.write(f"\n**{away} (Visita) = {l_away:.4f}**\n")
            f.write(f"- *Fuerza Ataque*: {bd_away['atts']} (Pond: {bd_away['w_curr']} Actual + {bd_away['w_prior']} Prior)\n")
            f.write(f"- *Fuerza Defensa Rival*: {bd_away['defs']}\n")
            f.write(f"- *Media Liga Visita*: {bd_away['league_avg']}\n")
            f.write(f"- *Cálculo Base*: {bd_away['atts']} * {bd_away['defs']} * {bd_away['league_avg']} = {bd_away['raw_lambda']}\n")
            if bd_away.get('note'):
                f.write(f"- ⚡ *Ajuste DOM*: {bd_away['note']}\n")
            
            # ===== NUEVA SECCIÓN: BREAKDOWN COMPLETO DE AJUSTES =====
            f.write("\n**📊 Desglose Completo de Ajustes:**\n")
            
            # Use ORIGINAL lambdas (before roster/context adjustments) as base
            lambda_home_base = p.get('lambdas_original', {}).get('home', l_home)
            lambda_away_base = p.get('lambdas_original', {}).get('away', l_away)
            
            # Show transition: base -> final
            f.write(f"```\n")
            f.write(f"{home} (Local):\n")
            f.write(f"  λ_base  = {lambda_home_base:.4f}\n")
            if len(p["correction_logs"]) > 0:
                for log in p["correction_logs"]:
                    # Use side tag for reliable filtering
                    if log.startswith("[HOME]"):
                        f.write(f"  {log}\n")
            f.write(f"  λ_final = {l_home:.4f}\n")
            
            home_impact = ((l_home / lambda_home_base) - 1.0) * 100 if lambda_home_base > 0 else 0
            f.write(f"  Impacto Total: {home_impact:+.1f}%\n")
            f.write(f"\n")
            
            f.write(f"{away} (Visita):\n")
            f.write(f"  λ_base  = {lambda_away_base:.4f}\n")
            if len(p["correction_logs"]) > 0:
                for log in p["correction_logs"]:
                    # Use side tag for reliable filtering
                    if log.startswith("[AWAY]"):
                        f.write(f"  {log}\n")
            f.write(f"  λ_final = {l_away:.4f}\n")
            
            away_impact = ((l_away / lambda_away_base) - 1.0) * 100 if lambda_away_base > 0 else 0
            f.write(f"  Impacto Total: {away_impact:+.1f}%\n")
            f.write(f"```\n")
            
            # Explanation of what this means
            if abs(home_impact) > 5 or abs(away_impact) > 5:
                f.write(f"\n**🔍 Interpretación:**\n")
                if abs(home_impact) > 10:
                    direction = "AUMENTÓ" if home_impact > 0 else "DISMINUYÓ"
                    f.write(f"- Los ajustes {direction} significativamente ({home_impact:+.1f}%) los goles esperados de {home}\n")
                if abs(away_impact) > 10:
                    direction = "AUMENTÓ" if away_impact > 0 else "DISMINUYÓ"
                    f.write(f"- Los ajustes {direction} significativamente ({away_impact:+.1f}%) los goles esperados de {away}\n")
                
                f.write(f"- Esto modifica las probabilidades de resultado y marcador final\n")
            
            # Legacy warnings section (for context validation errors)
            warnings_only = [log for log in p["correction_logs"] if "[WARNING]" in log]
            if warnings_only:
                f.write("\n**⚠️ Advertencias de Validación:**\n")
                for log in warnings_only:
                    f.write(f"- `{log}`\n")
            
            f.write("\n")
            
            # Outcome Probs
            pops = p["outcome_probs"]
            f.write(f"**Probabilidades Generales:** Local {pops['HOME']:.1%} | Empate {pops['DRAW']:.1%} | Visita {pops['AWAY']:.1%}\n\n")
            
            # EV Table
            f.write(f"### 🎯 Mejores Opciones (Ranking por Valor Esperado)\n")
            f.write("| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            
            for c in p["candidates_ev"]:
                is_best = "**" if c["score"] == p["pick_final"] else ""
                # Construct string first to avoid nested f-string weirdness
                row = f"| {is_best}{c['score']}{is_best} | {c['trend']} | {c['p']:.1%} | {c['p_trend']:.1%} | {is_best}{c['ev']:.3f}{is_best} |\n"
                f.write(row)
            
            f.write("\n")
            
            # Add to summary
            best = p["candidates_ev"][0]
            summary_rows.append(f"| {home} vs {away} | **{best['score']}** | EV: {best['ev']:.3f} | {best['trend']} ({best['p_trend']:.0%}) |")
            
        f.write("# 🏆 Resumen Final: Picks Recomendados\n\n")
        f.write("| Partido | Pick Óptimo | Valor (Puntos Esp.) | Tendencia Base |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        for row in summary_rows:
            f.write(f"{row}\n")
            
    # print(f"Reporte generado: {filename}", file=sys.stderr)

if __name__ == "__main__":
    import glob
    import re
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None, help="Path to input JSON (default: auto-detect latest jornada)")
    parser.add_argument("--force", action="store_true", help="Force execution ignoring critical validation errors")
    args = parser.parse_args()
    
    input_file = args.input
    
    # Auto-detection logic
    if input_file is None:
        # Try to find 'jornada X.json' files
        files = glob.glob("jornada *.json")
        if not files:
            # Fallback to hardcoded default if no pattern matches
            input_file = "input_matches.json"
        else:
            # Sort by number in filename
            def get_jornada_num(fname):
                match = re.search(r"jornada\s+(\d+)", fname, re.IGNORECASE)
                return int(match.group(1)) if match else 0
            
            latest_file = max(files, key=get_jornada_num)
            input_file = latest_file
            print(f"Auto-detected latest input file: '{input_file}'")

    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' not found.")
        print("   Please provide a file with --input or ensure 'jornada X.json' exists.")
        exit(1)
    
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Pass force mode to simulation
    run_simulation(data, force_mode=args.force)

import json
import math
import hashlib
import argparse
import random
import logging
from datetime import datetime
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

# --- Configuration & Constants ---
LEAGUE_AVG_HOME_G = 1.81
LEAGUE_AVG_AWAY_G = 1.29
LEAGUE_AVG_GLOBAL = (LEAGUE_AVG_HOME_G + LEAGUE_AVG_AWAY_G) / 2
DEFAULT_RHO = -0.13  # Standard Dixon-Coles correlation parameter

# Pre-computed Factorials (Buffer up to 30 for high scoring games)
FACTORIALS = [math.factorial(i) for i in range(31)]

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Absence Penalty Configuration
ABSENCE_PENALTIES = {
    ("portero", "alta"):       ("OPP", 1.20, "Aumento Lambda Rival (20%) por baja Portero Titular"),
    ("portero", "media"):      ("OPP", 1.10, "Aumento Lambda Rival (10%) por baja Portero Rotación"),
    
    ("defensor", "alta"):      ("OPP", 1.15, "Aumento Lambda Rival (15%) por baja Defensor Lider"),
    ("defensor", "media"):     ("OPP", 1.07, "Aumento Lambda Rival (7%) por baja Defensor"),
    
    ("mediocampista", "alta"): ("SELF", 0.90, "Reducción Lambda Propio (10%) por baja Creativo Top"),
    ("mediocampista", "media"):("SELF", 0.95, "Reducción Lambda Propio (5%) por baja Mediocampista"),
    
    ("atacante", "alta"):      ("SELF", 0.85, "Reducción Lambda Propio (15%) por baja Goleador Top"),
    ("atacante", "media"):     ("SELF", 0.92, "Reducción Lambda Propio (8%) por baja Atacante"),
}

# --- Data Structures ---

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

    def total_pj_curr(self) -> int:
        return self.pj_curr_home + self.pj_curr_away

@dataclass
class Absence:
    name: str
    role: str
    importance: str
    affects_match: bool
    evidence_level: str

# --- Core Logic ---

def get_deterministic_seed(home: str, away: str, jornada: str) -> int:
    """
    Generates a deterministic seed based on match metadata.
    """
    raw_str = f"{home} vs {away} | {jornada}"
    return int(hashlib.md5(raw_str.encode("utf-8")).hexdigest()[:8], 16)

def validate_match_entry(m: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates a single match entry. Returns (IsValid, Reason).
    Does NOT raise exceptions, allowing the main loop to skip bad matches gracefully.
    """
    match_meta = m.get("match", {})
    home = match_meta.get("home", "Unknown")
    away = match_meta.get("away", "Unknown")
    label = f"{home} vs {away}"

    # 1. Check strict hard missing
    uncertainty = m.get("uncertainty", {})
    if uncertainty.get("hard_missing_critical"):
        return False, f"Skipping {label}: flagged as hard_missing_critical."

    stats = m.get("stats", {})
    required_sides = ["home", "away"]
    
    for side in required_sides:
        s = stats.get(side, {})
        clausura = s.get("clausura_2026", {})
        apertura = s.get("apertura_2025", {})
        
        # Check prior season exist and PJ is 17
        if not apertura or apertura.get("PJ") != 17:
             return False, f"Skipping {label}: Invalid Apertura 2025 stats for {side}. PJ != 17."
             
        # Check current season strict granular stats
        keys = ["GF_home", "GC_home", "PJ_home", "GF_away", "GC_away", "PJ_away"]
        if any(k not in clausura for k in keys):
             return False, f"Skipping {label}: Missing granular stats for {side} in Clausura 2026."
        
        # Hard Source Check
        has_data = any(clausura.get(k, 0) > 0 for k in keys)
        if has_data:
            source = clausura.get("source", {})
            if not source or source.get("evidence_level") == "no_confirmado":
                 if "stats_missing" not in uncertainty.get("hard_missing_critical", []):
                     return False, f"Skipping {label}: Stats for {side} marked 'no_confirmado'."
                     
    return True, ""

def parse_team_stats(side_data: Dict[str, Any], name: str) -> TeamStats:
    curr = side_data["clausura_2026"]
    prev = side_data["apertura_2025"]
    
    return TeamStats(
        name=name,
        gf_curr_home=float(curr.get("GF_home", 0)), 
        gc_curr_home=float(curr.get("GC_home", 0)), 
        pj_curr_home=int(curr.get("PJ_home", 0)),
        gf_curr_away=float(curr.get("GF_away", 0)), 
        gc_curr_away=float(curr.get("GC_away", 0)), 
        pj_curr_away=int(curr.get("PJ_away", 0)),
        gf_prior=prev.get("GF", 0), 
        gc_prior=prev.get("GC", 0), 
        pj_prior=prev.get("PJ", 17)
    )

def calculate_lambda(attack_stats: TeamStats, defense_stats: TeamStats, is_home: bool) -> Tuple[float, Dict[str, Any]]:
    # --- Shrinkage Weight Calculation ---
    total_pj_curr = attack_stats.total_pj_curr()
    w_curr = min(0.85, (total_pj_curr / 17.0) * 0.85)
    w_prior = 1.0 - w_curr
    
    # --- Attack Strength ---
    if is_home:
        avg_gf_curr = attack_stats.gf_curr_home / max(1, attack_stats.pj_curr_home)
        atts_curr = avg_gf_curr / LEAGUE_AVG_HOME_G if LEAGUE_AVG_HOME_G > 0 else 1.0
        avg_gf_prior = attack_stats.gf_prior / attack_stats.pj_prior
        atts_prior = avg_gf_prior / LEAGUE_AVG_GLOBAL
    else:
        avg_gf_curr = attack_stats.gf_curr_away / max(1, attack_stats.pj_curr_away)
        atts_curr = avg_gf_curr / LEAGUE_AVG_AWAY_G if LEAGUE_AVG_AWAY_G > 0 else 1.0
        avg_gf_prior = attack_stats.gf_prior / attack_stats.pj_prior
        atts_prior = avg_gf_prior / LEAGUE_AVG_GLOBAL
    
    atts_final = (atts_curr * w_curr) + (atts_prior * w_prior)
    
    # --- Defense Strength ---
    if is_home:
        avg_gc_curr = defense_stats.gc_curr_away / max(1, defense_stats.pj_curr_away)
        defs_curr = avg_gc_curr / LEAGUE_AVG_HOME_G
    else:
        avg_gc_curr = defense_stats.gc_curr_home / max(1, defense_stats.pj_curr_home)
        defs_curr = avg_gc_curr / LEAGUE_AVG_AWAY_G

    avg_gc_prior = defense_stats.gc_prior / defense_stats.pj_prior
    defs_prior = avg_gc_prior / LEAGUE_AVG_GLOBAL
    
    defs_final = (defs_curr * w_curr) + (defs_prior * w_prior)
    
    # --- Final Lambda Calculation ---
    if is_home:
        expected_goals = atts_final * defs_final * LEAGUE_AVG_HOME_G
    else:
        expected_goals = atts_final * defs_final * LEAGUE_AVG_AWAY_G
        
    final_val = max(0.1, expected_goals)
    
    breakdown = {
        "atts": round(atts_final, 3),
        "defs": round(defs_final, 3),
        "w_curr": round(w_curr, 2),
        "w_prior": round(w_prior, 2),
        "league_avg": LEAGUE_AVG_HOME_G if is_home else LEAGUE_AVG_AWAY_G,
        "raw_lambda": round(final_val, 3)
    }
        
    return final_val, breakdown

def apply_absences(lambdas: Dict[str, float], match_data: Dict[str, Any]) -> Tuple[Dict[str, float], List[str]]:
    absences = match_data.get("absences", {})
    new_lambdas = lambdas.copy()
    logs = []
    
    valid_sources = ["oficial_club", "liga_mx_oficial", "medio_top"]

    def process_team_absences(team_key: str, opponent_key: str, team_label: str):
        for p in absences.get(team_key, []):
            if p.get("evidence_level") not in valid_sources: continue
            
            affects = p.get("affects_match")
            if isinstance(affects, str):
                affects = (affects.lower() == "true")
            
            if not affects: continue 
            
            role = p.get("role")
            imp = p.get("importance")
            name = p.get("name", "Jugador")
            
            effect = ABSENCE_PENALTIES.get((role, imp))
            if not effect: continue
            
            target, multiplier, msg_base = effect
            
            if target == "SELF":
                new_lambdas[team_key] *= multiplier
                logs.append(f"{msg_base} ({team_label}): {name}")
            else: # OPP
                new_lambdas[opponent_key] *= multiplier
                logs.append(f"{msg_base} ({team_label}): {name}")

    process_team_absences("home", "away", "Local")
    process_team_absences("away", "home", "Visita")
            
    return new_lambdas, logs

def poisson_pmf(k: int, lam: float) -> float:
    if k < 0: return 0.0
    k_fact = FACTORIALS[k] if k < len(FACTORIALS) else math.factorial(k)
    return (math.exp(-lam) * (lam ** k)) / k_fact

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

def get_outcome(h: int, a: int) -> str:
    if h > a: return "HOME"
    if a > h: return "AWAY"
    return "DRAW"

def calculate_exact_probabilities(lambda_h: float, lambda_a: float, limit: int) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
    """
    Computes exact probabilities using a dynamic limit.
    """
    matrix_probs = []
    total_prob_covered = 0.0
    probs_by_outcome = {"HOME": 0.0, "DRAW": 0.0, "AWAY": 0.0}
    
    for x in range(limit + 1):
        for y in range(limit + 1):
            p_raw = poisson_pmf(x, lambda_h) * poisson_pmf(y, lambda_a)
            p_adj = dixon_coles_adjustment(p_raw, x, y, lambda_h, lambda_a, DEFAULT_RHO)
            
            if p_adj < 0: p_adj = 0.0
            
            score_str = f"{x}-{y}"
            outcome = get_outcome(x, y)
            
            probs_by_outcome[outcome] += p_adj
            total_prob_covered += p_adj
            
            matrix_probs.append({
                "score": score_str,
                "p": p_adj,
                "outcome": outcome,
                "goals": x + y
            })
            
    # Normalize
    if total_prob_covered > 0:
        factor = 1.0 / total_prob_covered
        for item in matrix_probs:
             item["p"] *= factor
        for k in probs_by_outcome:
             probs_by_outcome[k] *= factor
             
    # Sort by probability DESC (default view)
    matrix_probs.sort(key=lambda x: x["p"], reverse=True)
    
    return probs_by_outcome, matrix_probs

def run_simulation(data: Dict[str, Any]) -> None:
    matches = data.get("matches", [])
    if not matches:
        print("No matches found in input.")
        return
        
    all_predictions = []
    
    for match_entry in matches:
        # 1. Validation Logic Injection
        is_valid, validation_msg = validate_match_entry(match_entry)
        if not is_valid:
            # Skip invalid match without crashing
            print(f"⚠️ [SKIP] {validation_msg}")
            continue

        match_meta = match_entry["match"]
        home_name = match_meta["home"]
        away_name = match_meta["away"]
        jornada = match_meta["jornada"]
        
        seed_val = get_deterministic_seed(home_name, away_name, jornada)
        
        # Stats & Lambdas
        home_stats = parse_team_stats(match_entry["stats"]["home"], home_name)
        away_stats = parse_team_stats(match_entry["stats"]["away"], away_name)
        
        lambda_home, bd_home = calculate_lambda(home_stats, away_stats, is_home=True)
        lambda_away, bd_away = calculate_lambda(away_stats, home_stats, is_home=False)
        lambdas = {"home": lambda_home, "away": lambda_away}
        lambdas, logs = apply_absences(lambdas, match_entry)
        
        # 2. Dynamic Limit Calculation
        max_l = max(lambdas["home"], lambdas["away"])
        # Poisson tail rule: Lambda + 6*Sigma covers >99.99%
        # Sigma = sqrt(Lambda)
        calc_limit = max(10, int(max_l + (6 * math.sqrt(max_l))))
        
        # --- Exact Calculation ---
        outcome_probs, candidates_all = calculate_exact_probabilities(lambdas["home"], lambdas["away"], limit=calc_limit)
        
        # 3. EV Analysis on ALL scores (not just top 10)
        processed_candidates = []
        for c in candidates_all: 
            # Optimization: Skip scores with near-zero probability to save memory/processing
            if c["p"] < 0.0001: continue 

            p_exact = c["p"]
            outcome_trend = c["outcome"]
            p_trend = outcome_probs[outcome_trend]
            
            ev = p_exact + p_trend
            
            processed_candidates.append({
                "score": c["score"],
                "p": round(p_exact, 4),
                "trend": outcome_trend,
                "p_trend": round(p_trend, 4),
                "ev": round(ev, 4)
            })
            
        # Sort by EV DESC
        processed_candidates.sort(key=lambda x: x["ev"], reverse=True)
        best_pick = processed_candidates[0]["score"]
        
        output = {
            "match": {
                "home": home_name,
                "away": away_name,
                "jornada": jornada
            },
            "seed": seed_val,
            "lambdas": lambdas,
            "calc_limit": calc_limit,
            "breakdown": {
                "home": bd_home,
                "away": bd_away
            },
            "correction_logs": logs,
            "outcome_probs": {k: round(v, 4) for k, v in outcome_probs.items()},
            # Return top 12 by EV for the report to keep JSON clean but informative
            "candidates_ev": processed_candidates[:12],
            "pick_final": best_pick,
            "notes": [f"Dynamic Limit: {calc_limit}", "Full Search EV Optimization"]
        }
        
        print(json.dumps(output, indent=2))
        all_predictions.append(output)

    generate_markdown_report(all_predictions)

def generate_markdown_report(predictions: List[Dict[str, Any]]) -> None:
    filename = "reporte_tecnico_automatico.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# 🔢 Reporte Técnico: V3 (Full EV + Dynamic Limits)\n\n")
        f.write(f"**Generado:** {datetime.now().isoformat()}\n")
        f.write("**Estrategia:** EV Search en TODOS los marcadores probables.\n")
        f.write("**Validación:** Skip-on-Error activado.\n\n")
        f.write("---\n\n")
        
        summary_rows = []
        
        for p in predictions:
            home = p["match"]["home"]
            away = p["match"]["away"]
            l_home = p["lambdas"]["home"]
            l_away = p["lambdas"]["away"]
            limit = p.get("calc_limit", 10)
            
            f.write(f"## {home} vs. {away}\n")
            f.write(f"### 🧪 Goles Esperados (Lambdas)\n")
            
            # Detailed Breakdown for Home
            bd_home = p["breakdown"]["home"]
            f.write(f"**{home}:** {l_home:.4f} (Limit: {limit})\n")
            f.write(f"> *Ataque:* {bd_home['atts']:.3f} | *Defensa Rival:* {bd_home['defs']:.3f} | *Media Liga:* {bd_home['league_avg']:.2f}\n")
            
            # Detailed Breakdown for Away
            bd_away = p["breakdown"]["away"]
            f.write(f"**{away}:** {l_away:.4f}\n")
            f.write(f"> *Ataque:* {bd_away['atts']:.3f} | *Defensa Rival:* {bd_away['defs']:.3f} | *Media Liga:* {bd_away['league_avg']:.2f}\n")

            
            # Logs
            if p["correction_logs"]:
                f.write("\n**⚠️ Ajustes:**\n")
                for log in p["correction_logs"]:
                    f.write(f"- {log}\n")
            
            f.write("\n")
            
            pops = p["outcome_probs"]
            f.write(f"**Probabilidades:** Local {pops['HOME']:.1%} | Empate {pops['DRAW']:.1%} | Visita {pops['AWAY']:.1%}\n\n")
            
            f.write(f"### 🎯 Mejores Picks (Ordenados por EV)\n")
            f.write("| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            
            for c in p["candidates_ev"]:
                is_best = "**" if c["score"] == p["pick_final"] else ""
                row = f"| {is_best}{c['score']}{is_best} | {c['trend']} | {c['p']:.1%} | {c['p_trend']:.1%} | {is_best}{c['ev']:.3f}{is_best} |\n"
                f.write(row)
            
            f.write("\n")
            
            best = p["candidates_ev"][0]
            summary_rows.append(f"| {home} vs {away} | **{best['score']}** | EV: {best['ev']:.3f} | {best['trend']} ({best['p_trend']:.0%}) |")
            
        f.write("# 🏆 Resumen Final\n\n")
        f.write("| Partido | Pick | Confianza (EV) | Tendencia |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        for row in summary_rows:
            f.write(f"{row}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=False, default="jornada 4.json", help="Path to input JSON")
    args = parser.parse_args()
    
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
        run_simulation(data)
    except FileNotFoundError:
        print(f"Error: File '{args.input}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in '{args.input}'.")

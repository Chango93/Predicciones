import json
import re
import os
import pandas as pd
from datetime import datetime
import src.predicciones.config as config
import src.predicciones.core as dl  # Alias dl to minimize refactor
from math import exp, factorial

import src.predicciones.data as data_loader

def poisson_prob(lambda_val, k):
    return (lambda_val**k * exp(-lambda_val)) / factorial(k)

def main():
    runtime_config = config.resolve_config()
    print(f"=== GENERADOR DE PREDICCIONES JORNADA {runtime_config.get('JORNADA', '?')} ===")
    
    # 1. Load Data/Setup
    print("Loading data...")
    print("Loading data...")
    with open(runtime_config['INPUT_MATCHES'], 'r', encoding='utf-8') as f:
        matches_data = json.load(f)
        
    stats_df = pd.read_csv(runtime_config['INPUT_STATS'], sep='\t')
    
    # 2. Parse Qualitative
    print("Parsing qualitative data...")
    # qualu_path = "Investigacion_cualitativa_jornada6.json"
    adj_map = data_loader.load_bajas_penalties(runtime_config['INPUT_EVALUATION']) # Uses eval json
    # Qualu adjust
    adj_map = data_loader.load_qualitative_adjustments(adj_map, runtime_config['INPUT_QUALITATIVE'])
    
    # Debug adjustments
    print("\nADJUSTMENTS APPLIED:")
    for team, data in adj_map.items():
        if data['att_adj'] != 1.0 or data['def_adj'] != 1.0:
            print(f"{team}: Att*{data['att_adj']:.2f}, Def*{data['def_adj']:.2f} | Notes: {data['notes']}")

    
    # 3. Build Stats
    team_stats_current, _ = dl.build_team_stats_canonical(stats_df, runtime_config['CURRENT_TOURNAMENT'])
    
    # MULTI-TOURNAMENT PRIOR (Weighted)
    print("Building Multi-Tournament Weighted Prior...")
    prior_weighted_stats = dl.build_weighted_prior_stats(stats_df, runtime_config)
    
    # Calculate League Avgs (Current only needed for main calculation)
    league_avg_curr = dl.calculate_league_averages_by_tournament(stats_df, runtime_config['CURRENT_TOURNAMENT'])
    # league_avg_prior not needed for computation anymore (baked into weighted stats) but verify signature
    
    # 4. Generate Predictions
    print("Generating predictions...")
    results = []
    
    print("\nPREDICCIONES Y METRICAS QUINIELA:")
    for match in matches_data['matches']:
        home_raw = match['match']['home']
        away_raw = match['match']['away']
        
        home_canon = dl.canonical_team_name(home_raw)
        away_canon = dl.canonical_team_name(away_raw)
        
        match_adjustments = {
            'home_att_adj': 1.0, 'home_def_adj': 1.0,
            'away_att_adj': 1.0, 'away_def_adj': 1.0
        }
        
        # Apply adjustments from adj_map
        if home_canon in adj_map:
             match_adjustments['home_att_adj'] = adj_map[home_canon].get('att_adj', 1.0)
             match_adjustments['home_def_adj'] = adj_map[home_canon].get('def_adj', 1.0)
        if away_canon in adj_map:
             match_adjustments['away_att_adj'] = adj_map[away_canon].get('att_adj', 1.0)
             match_adjustments['away_def_adj'] = adj_map[away_canon].get('def_adj', 1.0)
        
        # Compute Lambda Components
        try:
             comp, errors = dl.compute_components_and_lambdas(
                match, team_stats_current, 
                prior_weighted_stats,
                league_avg_curr, runtime_config,
                runtime_config['SHRINKAGE_DIVISOR_ACTUAL'], match_adjustments
            )
        except Exception as e:
            print(f"CRITICAL ERROR in {home_raw}-{away_raw}: {e}")
            continue
        
        if errors:
            print(f"Error in {home_raw}-{away_raw}: {errors}")
            continue
            
        l_home = comp['lambda_home_final']
        l_away = comp['lambda_away_final']
        
        # Simulate Score Grid (0-5 goals)
        prob_home_win = 0
        prob_draw = 0
        prob_away_win = 0
        
        scoreline_probs = []
        
        for h in range(6):
            for a in range(6):
                p = poisson_prob(l_home, h) * poisson_prob(l_away, a)
                scoreline_probs.append({'score': f"{h}-{a}", 'prob': p})
                
                if h > a: prob_home_win += p
                elif h == a: prob_draw += p
                else: prob_away_win += p
        
        # Metrics for Quiniela
        scoreline_probs.sort(key=lambda x: x['prob'], reverse=True)
        top_5 = scoreline_probs[:5]
        
        # Pick Exact (Most probable exact score)
        pick_exact = top_5[0]['score']
        
        # Pick 1X2 (Result prediction)
        if prob_home_win > max(prob_draw, prob_away_win):
            pick_1x2 = '1'
        elif prob_away_win > max(prob_home_win, prob_draw):
            pick_1x2 = '2'
        else:
            pick_1x2 = 'X'
            
        # Expected Value metric (Probability of Exact + Probability of Result)
        # This approximates a "confidence score" for the combined prediction
        ev = top_5[0]['prob'] + max(prob_home_win, prob_draw, prob_away_win)
        
        # Qualitative Notes
        notes_home = adj_map.get(home_canon, {}).get('notes', [])
        notes_away = adj_map.get(away_canon, {}).get('notes', [])
        notes_compact = ' | '.join(notes_home + notes_away) if notes_home or notes_away else ''

        # Print summary
        print(f"\n{home_raw} vs {away_raw}")
        print(f"  Lambda Final: {l_home:.2f} - {l_away:.2f}")
        print(f"  Probs: 1({prob_home_win:.1%}) X({prob_draw:.1%}) 2({prob_away_win:.1%})")
        print(f"  Pick: {pick_1x2} (Exact: {pick_exact}) | EV: {ev:.3f}")
        
        results.append({
            'home_team_canonical': home_canon,
            'away_team_canonical': away_canon,
            'lambda_home_final': l_home,
            'lambda_away_final': l_away,
            'prob_home_win': prob_home_win,
            'prob_draw': prob_draw,
            'prob_away_win': prob_away_win,
            'top_5_scorelines': '|'.join([f"{s['score']}:{s['prob']:.3f}" for s in top_5]),
            'pick_exact': pick_exact,
            'pick_1x2': pick_1x2,
            'ev': ev,
            'qualitative_notes': notes_compact,
            # Legacy fields for quick view
            'L_Home_Final': l_home,
            'L_Away_Final': l_away
        })

    # Save CSV
    jornada = runtime_config.get('JORNADA', 'X')
    out_file = f'predicciones_jornada_{jornada}_final.csv'
    df = pd.DataFrame(results)
    
    # Reorder columns for usability
    cols = ['home_team_canonical', 'away_team_canonical', 'pick_1x2', 'pick_exact', 'ev', 
            'prob_home_win', 'prob_draw', 'prob_away_win', 
            'lambda_home_final', 'lambda_away_final', 
            'top_5_scorelines', 'qualitative_notes']
    
    # Ensure all columns exist
    for c in cols:
        if c not in df.columns:
            df[c] = None
            
    df = df[cols]
    df.to_csv(out_file, index=False)
    print(f"\nGuardado en {out_file}")

if __name__ == "__main__":
    main()

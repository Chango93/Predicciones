import json
import re
import os
import pandas as pd
from datetime import datetime
import src.predicciones.config as config
import src.predicciones.core as dl  # Alias dl to minimize refactor
import src.predicciones.data as data_loader
import src.predicciones.quiniela as qx

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
    adj_map = data_loader.load_perplexity_weekly_bajas(adj_map, runtime_config.get('INPUT_PERPLEXITY_BAJAS', 'data/inputs/perplexity_bajas_semana.json'))
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
        
        # Optimize pick for quiniela scoring (2 exacto / 1 resultado)
        quiniela = qx.optimize_pick_for_quiniela(l_home, l_away)
        prob_home_win = quiniela['prob_home_win']
        prob_draw = quiniela['prob_draw']
        prob_away_win = quiniela['prob_away_win']
        top_5 = quiniela['top_5_by_prob']
        pick_exact = quiniela['pick_exact']
        pick_1x2 = quiniela['pick_1x2']
        ev = quiniela['ev']
        
        # Qualitative Notes
        notes_home = adj_map.get(home_canon, {}).get('notes', [])
        notes_away = adj_map.get(away_canon, {}).get('notes', [])
        notes_compact = ' | '.join(notes_home + notes_away) if notes_home or notes_away else ''

        # Print summary
        print(f"\n{home_raw} vs {away_raw}")
        print(f"  Lambda Final: {l_home:.2f} - {l_away:.2f}")
        print(f"  Probs: 1({prob_home_win:.1%}) X({prob_draw:.1%}) 2({prob_away_win:.1%})")
        print(f"  Pick: {pick_1x2} (Exact: {pick_exact}) | EV: {ev:.3f} | Mass: {quiniela['captured_mass']:.3f}")
        
        results.append({
            'home_team_canonical': home_canon,
            'away_team_canonical': away_canon,
            'lambda_home_final': l_home,
            'lambda_away_final': l_away,
            'prob_home_win': prob_home_win,
            'prob_draw': prob_draw,
            'prob_away_win': prob_away_win,
            'top_5_scorelines': '|'.join([f"{s['score']}:{s['prob']:.3f}" for s in top_5]),
            'top_5_ev': '|'.join([f"{s['score']}:{s['ev']:.3f}" for s in quiniela['top_5_by_ev']]),
            'pick_exact': pick_exact,
            'pick_1x2': pick_1x2,
            'ev': ev,
            'ev_confidence_gap': quiniela['ev_confidence_gap'],
            'grid_max_goals': quiniela['grid_max_goals'],
            'captured_mass': quiniela['captured_mass'],
            'qualitative_notes': notes_compact,
            # Legacy fields for quick view
            'L_Home_Final': l_home,
            'L_Away_Final': l_away
        })

    # Save CSV
    jornada = runtime_config.get('JORNADA', 'X')
    out_file = f'outputs/predicciones_jornada_{jornada}_final.csv'
    df = pd.DataFrame(results)
    
    # Reorder columns for usability
    cols = ['home_team_canonical', 'away_team_canonical', 'pick_1x2', 'pick_exact', 'ev', 
            'prob_home_win', 'prob_draw', 'prob_away_win', 
            'lambda_home_final', 'lambda_away_final', 
            'top_5_scorelines', 'top_5_ev', 'ev_confidence_gap', 'grid_max_goals', 'captured_mass', 'qualitative_notes']
    
    # Ensure all columns exist
    for c in cols:
        if c not in df.columns:
            df[c] = None
            
    df = df[cols]
    df.to_csv(out_file, index=False)
    print(f"\nGuardado en {out_file}")

if __name__ == "__main__":
    main()

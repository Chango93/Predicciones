import json
import re
import os
import pandas as pd
from datetime import datetime
import src.predicciones.config as config
import src.predicciones.core as dl  # Alias dl to minimize refactor
import src.predicciones.data as data_loader
import src.predicciones.quiniela as qx
import src.predicciones.improvements as improvements

def should_abstain(prob_1, prob_x, prob_2, gap, config):
    """
    Determina si el modelo debe abstenerse de dar un pick.
    Criterio: Gap muy bajo Y las probabilidades están muy dispersas (aka no hay favorito claro).
    """
    threshold = config.get('ABSTAIN_GAP_THRESHOLD', 0.03)
    spread_threshold = config.get('ABSTAIN_SPREAD_THRESHOLD', 0.10)
    
    max_p = max(prob_1, prob_x, prob_2)
    min_p = min(prob_1, prob_x, prob_2)
    spread = max_p - min_p
    
    # Abstenerse si el gap es despreciable
    # Y ADEMAS la diferencia entre el más probable y el menos probable es pequeña (todo es ~33%)
    # O simplemente si el gap es muy chico (usuario pidió "Umbral de abstención gap < 0.03")
    # El usuario dijo: "gap < threshold and (max_p - min_p) < spread"
    # Pero también: "Pumas vs Monterrey (gap=0.003): activaría abstención."
    
    # Vamos a ser estrictos con la regla propuesta:
    is_tight = gap < threshold
    is_balanced = spread < spread_threshold 
    
    # Si es muy cerrado (< 0.03), ya es candidato a abstención.
    # Pero si hay un favorito claro (ej 60% vs 20%) y el EV gap es chico por alguna razón rara, 
    # quizá no queramos abstenernos.
    # La regla del usuario fue: "gap < threshold and (max_p - min_p) < spread"
    
    # Analisis J7 Pumas-Monterrey: P1=36%, P2=36%, X=26%. Spread ~10%. Gap 0.003.
    # Cumple ambas.
    
    return is_tight and is_balanced

def main():
    runtime_config = config.resolve_config()
    print(f"=== GENERADOR DE PREDICCIONES JORNADA {runtime_config.get('JORNADA', '?')} ===")
    
    # 1. Load Data/Setup
    print("Loading data...")

    with open(runtime_config['INPUT_MATCHES'], 'r', encoding='utf-8') as f:
        matches_data = json.load(f)
        
    stats_df = pd.read_csv(runtime_config['INPUT_STATS'], sep='\t')
    
    # 2. Parse Qualitative
    print("Parsing qualitative data (New Dedup Flow)...")
    
    # A. Collect Raw
    raw_manual = data_loader.collect_manual_bajas(runtime_config['INPUT_EVALUATION'])
    raw_perplexity = data_loader.collect_perplexity_bajas(runtime_config.get('INPUT_PERPLEXITY_BAJAS', 'data/inputs/perplexity_bajas_semana.json'))
    
    # B. Merge and Deduplicate
    all_bajas = raw_manual + raw_perplexity
    deduped_bajas = data_loader.deduplicate_bajas(all_bajas)
    
    print(f"  > Raw Manual: {len(raw_manual)} | Raw Perplexity: {len(raw_perplexity)}")
    print(f"  > Deduplicated Total: {len(deduped_bajas)} (Removed {len(all_bajas) - len(deduped_bajas)} duplicates)")
    
    # C. Apply
    adj_map = {} # Initialize empty
    data_loader.apply_bajas_list(adj_map, deduped_bajas)
    
    # D. Qualitative Context (Existing)
    adj_map = data_loader.load_qualitative_adjustments(adj_map, runtime_config['INPUT_QUALITATIVE'])
    
    # Debug adjustments
    print("\nADJUSTMENTS APPLIED:")
    for team, data in adj_map.items():
        if data['att_adj'] != 1.0 or data['def_adj'] != 1.0:
            print(f"{team}: Att*{data['att_adj']:.2f}, Def*{data['def_adj']:.2f} | Notes: {len(data['notes'])} items")

    
    # 3. Build Stats
    # OPTIMIZATION: Pre-calculate canonical names for stats_df
    if 'home_team_canonical' not in stats_df.columns:
        stats_df['home_team_canonical'] = stats_df['home_team'].apply(dl.canonical_team_name)
    if 'away_team_canonical' not in stats_df.columns:
        stats_df['away_team_canonical'] = stats_df['away_team'].apply(dl.canonical_team_name)

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
        
        
        # Calculate Recent Form
        form_mult_home, form_details_home = improvements.calculate_recent_form(
             stats_df, home_canon, match['match']['kickoff_datetime'], runtime_config.get('RECENT_FORM_GAMES', 5)
        )
        form_mult_away, form_details_away = improvements.calculate_recent_form(
             stats_df, away_canon, match['match']['kickoff_datetime'], runtime_config.get('RECENT_FORM_GAMES', 5)
        )
        
        match_adjustments = {
            'home_att_adj': 1.0, 'home_def_adj': 1.0,
            'away_att_adj': 1.0, 'away_def_adj': 1.0,
            'home_form_adj': form_mult_home,
            'away_form_adj': form_mult_away
        }
        
        # Log Form
        if abs(form_mult_home - 1.0) > 0.001:
             print(f"  > HOME FORM: {home_canon} {form_details_home['pct']:.2f} -> {form_mult_home:.3f}")
             if home_canon in adj_map:
                 adj_map[home_canon]['notes'].append(f"RECENT FORM: {form_details_home['points']}pts ({form_details_home['pct']*100:.0f}%) -> {form_mult_home:.3f}")

        if abs(form_mult_away - 1.0) > 0.001:
             print(f"  > AWAY FORM: {away_canon} {form_details_away['pct']:.2f} -> {form_mult_away:.3f}")
             if away_canon in adj_map:
                 adj_map[away_canon]['notes'].append(f"RECENT FORM: {form_details_away['points']}pts ({form_details_away['pct']*100:.0f}%) -> {form_mult_away:.3f}")
        
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
        ev_gap = quiniela['ev_confidence_gap']
        
        if ev_gap >= 0.10:
            conf_label = 'ALTO'
        elif ev_gap >= 0.02:
            conf_label = 'MEDIO'
        else:
            conf_label = 'BAJO (VOLADO)'
            
        # Abstention Logic
        if should_abstain(prob_home_win, prob_draw, prob_away_win, ev_gap, runtime_config):
            conf_label = 'SIN VENTAJA'
            pick_1x2 = 'N/A'
            pick_exact = 'N/A'
            
        # Qualitative Notes
        notes_str = ""
        if home_canon in adj_map and adj_map[home_canon]['notes']:
            notes_str += f"{' | '.join(adj_map[home_canon]['notes'])}"
        if away_canon in adj_map and adj_map[away_canon]['notes']:
            if notes_str: notes_str += " | "
            notes_str += f"{' | '.join(adj_map[away_canon]['notes'])}"

        results.append({
            'home_team_canonical': home_canon,
            'away_team_canonical': away_canon,
            'pick_1x2': pick_1x2,
            'pick_exact': pick_exact,
            'ev': quiniela['ev'],
            'prob_home_win': prob_home_win,
            'prob_draw': prob_draw,
            'prob_away_win': prob_away_win,
            'lambda_home_final': l_home,
            'lambda_away_final': l_away,
            'top_5_scorelines': "|".join([f"{x['score']}:{x['prob']:.3f}" for x in top_5]),
            'top_5_ev': "|".join([f"{x['score']}:{x['ev']:.3f}" for x in quiniela['top_5_by_ev']]),
            'ev_confidence_gap': quiniela['ev_confidence_gap'],
            'grid_max_goals': quiniela['grid_max_goals'],
            'captured_mass': quiniela['captured_mass'],
            'confidence_label': conf_label,
            'qualitative_notes': notes_str
        })
        notes_home = adj_map.get(home_canon, {}).get('notes', [])
        notes_away = adj_map.get(away_canon, {}).get('notes', [])
        notes_compact = ' | '.join(notes_home + notes_away) if notes_home or notes_away else ''

        # Print summary
        print(f"\n{home_raw} vs {away_raw}")
        print(f"  Lambda Final: {l_home:.2f} - {l_away:.2f}")
        print(f"  Probs: 1({prob_home_win:.1%}) X({prob_draw:.1%}) 2({prob_away_win:.1%})")
        print(f"  Pick: {pick_1x2} (Exact: {pick_exact}) | EV: {ev:.3f} | Mass: {quiniela['captured_mass']:.3f}")
        


    # Save CSV
    jornada = runtime_config.get('JORNADA', 'X')
    out_file = f'outputs/predicciones_jornada_{jornada}_final.csv'
    df = pd.DataFrame(results)
    
    # Reorder columns for usability
    cols = ['home_team_canonical', 'away_team_canonical', 'pick_1x2', 'pick_exact', 'ev', 
            'prob_home_win', 'prob_draw', 'prob_away_win', 
            'lambda_home_final', 'lambda_away_final', 
            'confidence_label', 'top_5_scorelines', 'top_5_ev', 'ev_confidence_gap', 'grid_max_goals', 'captured_mass', 'qualitative_notes']
    
    # Ensure all columns exist
    for c in cols:
        if c not in df.columns:
            df[c] = None
            
    df = df[cols]
    df = df.drop_duplicates(subset=['home_team_canonical', 'away_team_canonical'])
    df.to_csv(out_file, index=False)
    print(f"\nGuardado en {out_file}")

if __name__ == "__main__":
    main()

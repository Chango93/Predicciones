
import json
import re
import pandas as pd
from datetime import datetime
import src.predicciones.core as dl
import src.predicciones.config as config
from math import isnan

# === CONFIG (Same as gen_predicciones) ===
# ... (Repeated logic for parsing will be refined to capture text)

import src.predicciones.data as data_loader
import src.predicciones.quiniela as qx

def main():
    runtime_config = config.resolve_config()
    print("Generando Reporte Técnico Automático...")
    
    # Load inputs
    # Load Inputs
    with open(runtime_config['INPUT_MATCHES'], 'r', encoding='utf-8') as f:
        matches_data = json.load(f)
    stats_df = pd.read_csv(runtime_config['INPUT_STATS'], sep='\t')
    
    team_stats_current, _ = dl.build_team_stats_canonical(stats_df, runtime_config['CURRENT_TOURNAMENT'])
    # PRIOR MULTI
    print("Building Multi-Tournament Weights...")
    prior_weighted_stats = dl.build_weighted_prior_stats(stats_df, runtime_config)
    
    league_avg_curr = dl.calculate_league_averages_by_tournament(stats_df, runtime_config['CURRENT_TOURNAMENT'])
    
    # Parse Qualitative (Now Hybrid with Synced JSON)
    # Using the new consolidated loader
    adj_map = data_loader.load_bajas_penalties(runtime_config['INPUT_EVALUATION'])
    adj_map = data_loader.load_perplexity_weekly_bajas(adj_map, runtime_config.get('INPUT_PERPLEXITY_BAJAS', 'data/inputs/perplexity_bajas_semana.json'))
    adj_map = data_loader.load_qualitative_adjustments(adj_map, runtime_config['INPUT_QUALITATIVE'])
    
    # We no longer check for 'ligamx_clausura2026_injuries.json' separately as logic is merged.   
    # OUTPUT MARKDOWN BUILDER
    md_output = []
    # ... header lines ...
    md_output.append(f"# 🔢 Reporte Técnico: Jornada {runtime_config.get('JORNADA', '?')} (Liga MX)")
    md_output.append(f"**Generado:** {datetime.now().isoformat()}")
    md_output.append(f"**Estrategia:** Maximizar Puntos (Quiniela EV)")
    md_output.append(f"**Fórmula EV:** Prob. Exacta + Prob. Resultado")
    md_output.append(f"**Prior:** Multi-Torneo Ponderado (Estabilidad Aumentada)")
    md_output.append(f"\n---")
    
    summary_picks = []

    for match in matches_data['matches']:
        home_raw = match['match']['home']
        away_raw = match['match']['away']
        home_canon = dl.canonical_team_name(home_raw)
        away_canon = dl.canonical_team_name(away_raw)
        
        # Get Data
        home_data = adj_map.get(home_canon, {'att_adj':1.0, 'def_adj':1.0, 'report_log':[], 'context_txt':[], 'ausencias_txt':[], 'movimientos_txt':[]})
        away_data = adj_map.get(away_canon, {'att_adj':1.0, 'def_adj':1.0, 'report_log':[], 'context_txt':[], 'ausencias_txt':[], 'movimientos_txt':[]})
        
        match_adjustments = {
            'home_att_adj': home_data['att_adj'],
            'home_def_adj': home_data['def_adj'],
            'away_att_adj': away_data['att_adj'],
            'away_def_adj': away_data['def_adj'],
        }
        
        comp, errors = dl.compute_components_and_lambdas(match, team_stats_current, 
                                                         prior_weighted_stats, # CHANGED
                                                         league_avg_curr, runtime_config,
                                                         runtime_config['SHRINKAGE_DIVISOR_ACTUAL'], match_adjustments)
        
        if errors: continue

        l_home = comp['lambda_home_final']
        l_away = comp['lambda_away_final']
        l_home_base = comp['lambda_home_base']
        l_away_base = comp['lambda_away_base']
        
        # Probs + pick optimization for quiniela scoring
        quiniela = qx.optimize_pick_for_quiniela(l_home, l_away)
        prob_home = quiniela['prob_home_win']
        prob_draw = quiniela['prob_draw']
        prob_away = quiniela['prob_away_win']

        # Build Match Report Section
        md_output.append(f"\n## {home_raw} vs. {away_raw}")
        
        # --- QUINIELA METRICS ---
        top_5 = quiniela['top_5_by_prob']
        pick_exact = quiniela['pick_exact']
        pick_1x2_raw = quiniela['pick_1x2']
        pick_1x2 = {'1': '1 (Local)', 'X': 'X (Empate)', '2': '2 (Visita)'}[pick_1x2_raw]
        prob_res = {'1': prob_home, 'X': prob_draw, '2': prob_away}[pick_1x2_raw]
        ev = quiniela['ev']
        
        md_output.append(f"\n### 🎯 Pronóstico Quiniela")
        md_output.append(f"- **Pick 1X2:** {pick_1x2} (Prob: {prob_res:.1%})")
        md_output.append(f"- **Pick Exacto:** {pick_exact} (Prob: {top_5[0]['prob']:.1%})")
        md_output.append(f"- **Valor Esperado (EV):** {ev:.3f}")
        md_output.append(f"- **Confianza del pick (gap EV):** {quiniela['ev_confidence_gap']:.3f}")
        md_output.append(f"- **Top 5 Marcadores:**")
        for s in top_5:
            md_output.append(f"  - {s['score']}: {s['prob']:.1%}")
            
        # --- END QUINIELA METRICS ---
        
        # Context
        md_output.append(f"### 🗞️ Contexto y Novedades")
        for line in home_data['context_txt'] + away_data['context_txt']:
            md_output.append(line)
        if not home_data['context_txt'] and not away_data['context_txt']:
            md_output.append("- *Sin contexto crítico destacado.*")
            
        md_output.append(f"\n**Movimientos de Mercado:**")
        for line in home_data['movimientos_txt'] + away_data['movimientos_txt']:
            md_output.append(line)
            
        md_output.append(f"\n**Ausencias Relevantes:**")
        for line in home_data['ausencias_txt'] + away_data['ausencias_txt']:
            md_output.append(line)
            
        # Analysis
        md_output.append(f"\n### 🧪 Análisis de Lambdas (Goles Esperados)")
        
        # Home Analysis
        # Att Force = att_home_rel_blend
        att_force_h = comp['att_home_rel_blend']
        def_force_a = comp['def_away_rel_blend']
        avg_h = league_avg_curr['home']
        
        md_output.append(f"**{home_raw} (Local) = {l_home:.4f}**")
        md_output.append(f"- *Fuerza Ataque*: {att_force_h:.3f}")
        md_output.append(f"- *Fuerza Defensa Rival*: {def_force_a:.3f}")
        md_output.append(f"- *Media Liga Local*: {avg_h:.3f}")
        md_output.append(f"- *Cálculo Base*: {att_force_h:.3f} * {def_force_a:.3f} * {avg_h:.3f} = {l_home_base:.3f}")
        
        # Away Analysis
        att_force_a = comp['att_away_rel_blend']
        def_force_h = comp['def_home_rel_blend']
        avg_a = league_avg_curr['away']
        
        md_output.append(f"\n**{away_raw} (Visita) = {l_away:.4f}**")
        md_output.append(f"- *Fuerza Ataque*: {att_force_a:.3f}")
        md_output.append(f"- *Fuerza Defensa Rival*: {def_force_h:.3f}")
        md_output.append(f"- *Media Liga Visita*: {avg_a:.3f}")
        md_output.append(f"- *Cálculo Base*: {att_force_a:.3f} * {def_force_h:.3f} * {avg_a:.3f} = {l_away_base:.3f}")
        
        # Adjustments Table
        md_output.append(f"\n**📊 Desglose Completo de Ajustes:**")
        md_output.append("```")
        
        # Home Log
        md_output.append(f"{home_raw} (Local):")
        md_output.append(f"  λ_base  = {l_home_base:.4f}")
        # Add Home-specific adjustments (those affecting lambda_home)
        # 1. Home Attack Adjustments
        for adj in home_data['report_log']:
            if "Lambda Propio" in adj['desc']: 
                 md_output.append(f"  [HOME] [{adj['pct']:+.1f}%] {adj['desc']}")
            elif "Contexto" in adj['desc']: # Allow Context messages
                 md_output.append(f"  [HOME] [{adj['pct']:+.1f}%] {adj['desc']}")

        # 2. Away Defense Adjustments (affect Home Goals)
        for adj in away_data['report_log']:
            if "Lambda Rival" in adj['desc']: # Increases Home Goals
                 md_output.append(f"  [HOME] [{adj['pct']:+.1f}%] {adj['desc']} (en {away_raw})")
                 
        md_output.append(f"  λ_final = {l_home:.4f}")
        impact_h = ((l_home - l_home_base) / l_home_base) * 100
        md_output.append(f"  Impacto Total: {impact_h:+.1f}%")

        md_output.append("")
        
        # Away Log
        md_output.append(f"{away_raw} (Visita):")
        md_output.append(f"  λ_base  = {l_away_base:.4f}")
        # Away adjustments
        for adj in away_data['report_log']:
            if "Lambda Propio" in adj['desc']:
                 md_output.append(f"  [AWAY] [{adj['pct']:+.1f}%] {adj['desc']}")
            elif "Contexto" in adj['desc']:
                 md_output.append(f"  [AWAY] [{adj['pct']:+.1f}%] {adj['desc']}")
        for adj in home_data['report_log']:
            if "Lambda Rival" in adj['desc']:
                 md_output.append(f"  [AWAY] [{adj['pct']:+.1f}%] {adj['desc']} (en {home_raw})")
                 
        md_output.append(f"  λ_final = {l_away:.4f}")
        impact_a = ((l_away - l_away_base) / l_away_base) * 100
        md_output.append(f"  Impacto Total: {impact_a:+.1f}%")
        md_output.append("```")
        
        # Interpretacion
        md_output.append(f"\n**🔍 Interpretación:**")
        md_output.append(f"- Probabilidades Generales: Local {prob_home*100:.1f}% | Empate {prob_draw*100:.1f}% | Visita {prob_away*100:.1f}%")
        
        # EV Table
        md_output.append(f"\n### 🎯 Mejores Opciones (Ranking por Valor Esperado)")
        md_output.append(f"| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |")
        md_output.append(f"| :--- | :--- | :--- | :--- | :--- |")
        
        # Generate options from grilla top (ordenadas por EV real de quiniela)
        options = []
        for item in quiniela['top_5_by_ev']:
            h, a = item['h'], item['a']
            p_exact = item['prob']

            if h > a:
                p_result = prob_home
                res_type = "HOME"
            elif h == a:
                p_result = prob_draw
                res_type = "DRAW"
            else:
                p_result = prob_away
                res_type = "AWAY"

            options.append({
                'score': item['score'],
                'type': res_type,
                'p_exact': p_exact,
                'p_gral': p_result,
                'ev': p_result + p_exact
            })

        # Sort by EV descending
        options.sort(key=lambda x: x['ev'], reverse=True)
        
        # Top 8
        for opt in options[:8]:
            md_output.append(f"| **{opt['score']}** | {opt['type']} | {opt['p_exact']*100:.1f}% | {opt['p_gral']*100:.1f}% | **{opt['ev']:.3f}** |")
            
        # Add to summary
        best = options[0]
        summary_picks.append({
            'match': f"{home_raw} vs {away_raw}",
            'pick': best['score'],
            'ev': best['ev'],
            'trend': f"{best['type']} ({best['p_gral']*100:.0f}%)"
        })
        
        md_output.append("\n---")

    # Final Summary
    md_output.append(f"\n# 🏆 Resumen Final: Picks Recomendados")
    md_output.append(f"| Partido | Pick Óptimo | Valor (Puntos Esp.) | Tendencia Base |")
    md_output.append(f"| :--- | :---: | :---: | :---: |")
    for s in summary_picks:
        md_output.append(f"| {s['match']} | **{s['pick']}** | EV: {s['ev']:.3f} | {s['trend']} |")
        
    # Write File (outputs + copia en raíz para consulta rápida)
    jornada = runtime_config.get('JORNADA', 'X')
    out_file = f'outputs/reporte_tecnico_jornada_{jornada}.md'
    root_file = f'reporte_tecnico_jornada_{jornada}.md'

    report_content = "\n".join(md_output)

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    with open(root_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"Reporte generado: {out_file}")
    print(f"Copia en raíz: {root_file}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()

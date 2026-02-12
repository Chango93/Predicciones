
import json
import os
import re
import src.predicciones.core as dl

# === CONFIGURACION DE PENALIZACIONES (Shared) ===
PENALTIES = {
    'GK_KEY': 1.15,      # Aumento en goles concedidos (Defensa debil)
    'DF_KEY': 1.10,      # Aumento en goles concedidos
    'DF_REG': 1.05,
    'MF_KEY': 0.90,      # Reduccion en ataque (Ataque debil)
    'MF_REG': 0.97,      # Ajustado de 0.95 a 0.97 segun calibracion
    'FW_KEY': 0.85,      # Reduccion en ataque
    'FW_REG': 0.93,      # Ajustado de 0.91 a 0.93 segun calibracion
    'STATUS_DUDA_FACTOR': 0.5, # Factor para reducir impacto si es Duda
}

def apply_minutes_gate(baja):
    """
    Gate: reduce impact si jugador sin minutos confirmados.
    Evita penalizaciones excesivas por jugadores suplentes sin minutos.
    
    Args:
        baja (dict): Diccionario de baja con campos: player, manual_impact_level, minutes_played
    
    Returns:
        str: Impact level ajustado ('High', 'Mid', 'Low')
    """
    minutes = baja.get('minutes_played', None)
    impact_orig = baja.get('manual_impact_level', 'Low')
    player = baja.get('player', 'Unknown')
    
    # Si no hay info de minutos, forzar max=Mid
    if minutes is None and impact_orig == 'High':
        print(f"⚠️ WARNING: {player} tiene impact='High' sin minutes_played. Downgrade a 'Mid'")
        return 'Mid'
    
    # Si tiene pocos minutos, no puede ser High
    if minutes is not None and minutes < 90 and impact_orig == 'High':
        print(f"⚠️ WARNING: {player} tiene {minutes} minutos < 90 con impact='High'. Downgrade a 'Mid'")
        return 'Mid'
    
    return impact_orig

def load_bajas_penalties(file_path="evaluacion_bajas.json"):
    """
    Loads structured bajas evaluation and applies penalties.
    Returns a dictionary with both numerical adjustments and reporting logs.
    """
    if not os.path.exists(file_path):
        print(f"WARNING: {file_path} not found. Returning empty adjustments.")
        return {}
        
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    bajas = data.get('bajas_identificadas', [])
    team_adjustments = {}
    
    for baja in bajas:
        team = dl.canonical_team_name(baja['team'])
        if team not in team_adjustments:
            team_adjustments[team] = {
                'att_adj': 1.0, 
                'def_adj': 1.0, 
                'notes': [],
                'report_log': [],     # For the report table
                'ausencias_txt': [],  # For the text section
            }
            
        role = baja.get('role', '').lower()
        status = baja.get('status', '').title()
        impact_level_orig = baja.get('manual_impact_level', 'Low') # High, Mid, Low, None
        impact_level = apply_minutes_gate(baja)  # 🔒 Aplicar gate
        player = baja.get('player', 'Unknown')
        reason = baja.get('reason', '')
        
        # Display Text (Report)
        icon = "🚑" if "Fuera" in status else "⚠️"
        ausencia_txt = f"{icon} **{player}** ({role}): {status} - *{reason}* [Impacto: {impact_level}]"
        team_adjustments[team]['ausencias_txt'].append(ausencia_txt)
        
        # 1. Determine Base Penalty
        if impact_level in ['Low', 'None', 'low', 'none']:
            continue
            
        # 2. Select Constants
        is_key = (impact_level == 'High')
        
        # 3. Apply Duda Factor
        is_duda = "duda" in status.lower()
        if is_duda:
            impact_factor = 0.0 # User requested to REMOVE Duda impact (from gen_predicciones logic)
        else:
            impact_factor = 1.0
        
        # 4. Apply to Role
        penalty_att = 1.0
        penalty_def = 1.0
        desc_log = ""
        pct_log = 0
        
        if "portero" in role:
            base = PENALTIES['GK_KEY'] if is_key else 1.05 
            effect = (base - 1.0) * impact_factor
            penalty_def = 1.0 + effect
            desc_log = "Lambda Rival (Portero)"
            pct_log = effect * 100
            
        elif "defensa" in role or "lateral" in role or "central" in role:
            base = PENALTIES['DF_KEY'] if is_key else PENALTIES['DF_REG']
            effect = (base - 1.0) * impact_factor
            penalty_def = 1.0 + effect
            desc_log = "Lambda Rival (Defensa)"
            pct_log = effect * 100
            
        elif "mediocampista" in role or "volante" in role:
            base = PENALTIES['MF_KEY'] if is_key else PENALTIES['MF_REG']
            effect = (1.0 - base) * impact_factor
            penalty_att = 1.0 - effect
            desc_log = "Lambda Propio (Medio)"
            pct_log = (penalty_att - 1.0) * 100
            
        elif "delantero" in role or "atacante" in role or "extremo" in role:
            base = PENALTIES['FW_KEY'] if is_key else PENALTIES['FW_REG']
            effect = (1.0 - base) * impact_factor
            penalty_att = 1.0 - effect
            desc_log = "Lambda Propio (Ataque)"
            pct_log = (penalty_att - 1.0) * 100
            
        # Apply
        curr = team_adjustments[team]
        curr['att_adj'] *= penalty_att
        curr['def_adj'] *= penalty_def
        curr['notes'].append(f"{player} ({role}): {impact_level}{' (Duda)' if is_duda else ''} -> att*{penalty_att:.3f}, def*{penalty_def:.3f}")
        
        if pct_log != 0:
            curr['report_log'].append({
                 'desc': f"{desc_log}: {player} ({status})", 
                 'pct': pct_log, 
                 'type': 'HOME' if 'Propio' in desc_log else 'AWAY'
            })
            
    return team_adjustments

def load_qualitative_adjustments(team_adjustments, qualitative_path="Investigacion_cualitativa_jornada6.json"):
    """
    Loads qualitative context and transfers.
    Updates the team_adjustments dictionary in place.
    """
    if not os.path.exists(qualitative_path):
        print(f"WARNING: {qualitative_path} not found. Skipping qualitative adjustments.")
        return team_adjustments
        
    with open(qualitative_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    lines = content.splitlines()
    current_section = None
    current_team = None
    current_context_type = None
    
    # Initialize keys if missing
    for team in team_adjustments:
        if 'movimientos_txt' not in team_adjustments[team]: team_adjustments[team]['movimientos_txt'] = []
        if 'context_txt' not in team_adjustments[team]: team_adjustments[team]['context_txt'] = []
        if 'report_log' not in team_adjustments[team]: team_adjustments[team]['report_log'] = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if "TRANSFERENCIAS" in line: current_section = 'transfers'; continue
        if "CONTEXTO" in line: current_section = 'context'; continue
        if "AUSENCIAS" in line: current_section = 'skip'; continue
        if "NOTAS" in line: current_section = 'skip'; continue
        
        if current_section == 'transfers':
            if "Equipo:" in line:
                tm_match = re.search(r"Equipo:\s*(.*?)\s*\|", line)
                ply_match = re.search(r"Jugador:\s*(.*?)\s*\|", line)
                if tm_match:
                    tm_name = dl.canonical_team_name(tm_match.group(1))
                    ply_name = ply_match.group(1) if ply_match else "Player"
                    
                    if tm_name not in team_adjustments:
                        team_adjustments[tm_name] = {
                            'att_adj': 1.0, 
                            'def_adj': 1.0, 
                            'notes': [], 
                            'report_log': [],
                            'ausencias_txt': [], 
                            'movimientos_txt': [], 
                            'context_txt': []
                        }
                    
                    # Ensure keys exist (if created above they do, if existed from bajas they might not have these specific lists)
                    if 'movimientos_txt' not in team_adjustments[tm_name]: team_adjustments[tm_name]['movimientos_txt'] = []
                    
                    # Apply Transfer Boost
                    team_adjustments[tm_name]['att_adj'] *= 1.02
                    team_adjustments[tm_name]['notes'].append(f"TRANSFER BOOST (+2%): {ply_name}")
                    team_adjustments[tm_name]['movimientos_txt'].append(f"- 🟢 **ALTA ({tm_name.title()}):** {ply_name}")
                    team_adjustments[tm_name]['report_log'].append({
                        'desc': f"BOOST Lambda Propio (Fichaje): {ply_name}", 
                        'pct': 2.0, 
                        'type': 'HOME'
                    })

        elif current_section == 'context':
            if line.startswith("Tipo:"):
                current_context_type = line.replace("Tipo:", "").strip()
            elif line.startswith("Afecta a:"):
                affects_line = line.replace("Afecta a:", "").strip()
                segments = [s.strip() for s in affects_line.split('/')]
                
                for segment in segments:
                    # Generic team checking - simplified for speed
                    # Ideally we have a list of all known alias keys from config/core
                    # but hardcoding the commons here covers 99%
                    for t_code in ['pumas', 'america', 'chivas', 'guadalajara', 'cruz azul', 'toluca', 'tigres', 'monterrey', 'pachuca', 'leon', 'santos', 'mazatlan', 'puebla', 'juarez', 'tijuana', 'necaxa', 'san luis', 'queretaro', 'atlas']:
                         if t_code in segment.lower():
                             tm_name = dl.canonical_team_name(t_code)
                             if tm_name not in team_adjustments:
                                 team_adjustments[tm_name] = {
                                     'att_adj': 1.0, 'def_adj': 1.0, 'notes': [], 
                                     'report_log': [], 'ausencias_txt': [], 'movimientos_txt': [], 'context_txt': []
                                 }
                             if 'context_txt' not in team_adjustments[tm_name]: team_adjustments[tm_name]['context_txt'] = []
                             if 'report_log' not in team_adjustments[tm_name]: team_adjustments[tm_name]['report_log'] = []

                             subtype_match = re.search(r"\(([^)]+)\)", segment)
                             team_subtype = subtype_match.group(1) if subtype_match else (current_context_type or "")
                             
                             if "momentum" in team_subtype.lower() and "crisis" not in team_subtype.lower():
                                 team_adjustments[tm_name]['att_adj'] *= 1.05
                                 team_adjustments[tm_name]['notes'].append(f"CONTEXT MOMENTUM (+5%): {team_subtype}")
                                 team_adjustments[tm_name]['report_log'].append({'desc': f"Contexto: {team_subtype}", 'pct': 5.0, 'type': 'HOME'})
                             elif "crisis" in team_subtype.lower() or ("extrema" in team_subtype.lower() and "crisis" in current_context_type.lower()):
                                 team_adjustments[tm_name]['att_adj'] *= 0.95
                                 team_adjustments[tm_name]['def_adj'] *= 1.05
                                 team_adjustments[tm_name]['notes'].append(f"CONTEXT CRISIS (-5% Att, -5% Def): {team_subtype}")
                                 team_adjustments[tm_name]['report_log'].append({'desc': f"Contexto: {team_subtype}", 'pct': -5.0, 'type': 'HOME'})
                             elif "winning_streak" in team_subtype.lower():
                                 team_adjustments[tm_name]['att_adj'] *= 1.03
                                 team_adjustments[tm_name]['notes'].append(f"CONTEXT WINNING STREAK (+3%): {team_subtype}")
                                 team_adjustments[tm_name]['report_log'].append({'desc': f"Contexto: Buena Forma (5 ganados)", 'pct': 3.0, 'type': 'HOME'})
                             
                             current_team = tm_name

            elif line.startswith("Evidencia:") and current_team:
                evidence = line.replace("Evidencia:", "").strip()
                if 'context_txt' not in team_adjustments[current_team]: team_adjustments[current_team]['context_txt'] = []
                team_adjustments[current_team]['context_txt'].append(f"- ℹ️ **CONTEXTO:** {evidence}")

    return team_adjustments

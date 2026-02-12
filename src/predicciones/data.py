
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

def load_bajas_penalties(file_path="data/inputs/evaluacion_bajas.json"):
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

def load_qualitative_adjustments(team_adjustments, qualitative_path="data/inputs/Investigacion_cualitativa_jornada6.json"):
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


def _ensure_team_adjustment(team_adjustments, team_name):
    """Inicializa estructura de ajustes por equipo si no existe."""
    if team_name not in team_adjustments:
        team_adjustments[team_name] = {
            'att_adj': 1.0,
            'def_adj': 1.0,
            'notes': [],
            'report_log': [],
            'ausencias_txt': [],
            'movimientos_txt': [],
            'context_txt': [],
        }

    # Garantizar llaves mínimas para evitar KeyError.
    team_adjustments[team_name].setdefault('att_adj', 1.0)
    team_adjustments[team_name].setdefault('def_adj', 1.0)
    team_adjustments[team_name].setdefault('notes', [])
    team_adjustments[team_name].setdefault('report_log', [])
    team_adjustments[team_name].setdefault('ausencias_txt', [])
    team_adjustments[team_name].setdefault('movimientos_txt', [])
    team_adjustments[team_name].setdefault('context_txt', [])



def _apply_scaled_adjustment(team_adjustments, team_name, player, role, impact_level, status, reason,
                             source='perplexity', confidence=0.75, recency_days=0):
    """
    Aplica ajuste de bajas con factor de confianza y recencia.

    Escala final = confidence * recency_factor
    recency_factor decae linealmente hasta 0.55 en 14 días.
    """
    _ensure_team_adjustment(team_adjustments, team_name)

    role_l = (role or '').lower()
    status_l = (status or '').lower()

    if (impact_level or '').lower() in ['low', 'none', 'unknown', 'desconocido']:
        return

    is_key = (impact_level or '').lower() == 'high'

    # Sin impacto en duda por diseño conservador
    if 'duda' in status_l:
        impact_factor = 0.0
    else:
        impact_factor = 1.0

    recency_days = max(0, min(30, int(recency_days or 0)))
    recency_factor = max(0.55, 1.0 - (recency_days / 31.0) * 0.45)
    scale = max(0.30, min(1.0, float(confidence or 0.75))) * recency_factor

    penalty_att = 1.0
    penalty_def = 1.0
    desc_log = ""
    pct_log = 0.0

    if "portero" in role_l:
        base = PENALTIES['GK_KEY'] if is_key else 1.05
        effect = (base - 1.0) * impact_factor * scale
        penalty_def = 1.0 + effect
        desc_log = f"Lambda Rival (Portero) [{source}]"
        pct_log = effect * 100
    elif "defensa" in role_l or "lateral" in role_l or "central" in role_l:
        base = PENALTIES['DF_KEY'] if is_key else PENALTIES['DF_REG']
        effect = (base - 1.0) * impact_factor * scale
        penalty_def = 1.0 + effect
        desc_log = f"Lambda Rival (Defensa) [{source}]"
        pct_log = effect * 100
    elif "mediocampista" in role_l or "volante" in role_l:
        base = PENALTIES['MF_KEY'] if is_key else PENALTIES['MF_REG']
        effect = (1.0 - base) * impact_factor * scale
        penalty_att = 1.0 - effect
        desc_log = f"Lambda Propio (Medio) [{source}]"
        pct_log = (penalty_att - 1.0) * 100
    elif "delantero" in role_l or "atacante" in role_l or "extremo" in role_l:
        base = PENALTIES['FW_KEY'] if is_key else PENALTIES['FW_REG']
        effect = (1.0 - base) * impact_factor * scale
        penalty_att = 1.0 - effect
        desc_log = f"Lambda Propio (Ataque) [{source}]"
        pct_log = (penalty_att - 1.0) * 100
    else:
        # Rol desconocido: ajuste mínimo conservador
        effect = 0.02 * scale * impact_factor
        penalty_att = 1.0 - effect
        desc_log = f"Lambda Propio (Rol no clasificado) [{source}]"
        pct_log = (penalty_att - 1.0) * 100

    curr = team_adjustments[team_name]
    curr['att_adj'] *= penalty_att
    curr['def_adj'] *= penalty_def

    icon = "🚑" if "fuera" in status_l or "out" in status_l else "⚠️"
    curr['ausencias_txt'].append(
        f"{icon} **{player}** ({role or 'N/A'}): {status or 'N/A'} - *{reason or 'Sin detalle'}* "
        f"[Impacto: {impact_level}, Confianza:{confidence:.2f}, Recencia:{recency_days}d]"
    )

    curr['notes'].append(
        f"{source.upper()} | {player} ({role}) impact={impact_level} conf={confidence:.2f} recency={recency_days}d"
    )

    curr['report_log'].append({
        'desc': f"{desc_log}: {player} ({status})",
        'pct': pct_log,
        'type': 'HOME' if 'Propio' in desc_log else 'AWAY'
    })



def load_perplexity_weekly_bajas(team_adjustments, file_path="data/inputs/perplexity_bajas_semana.json"):
    """
    Carga bajas semanales provenientes de Perplexity en JSON estructurado.

    Formato esperado:
    {
      "week_reference": "2026-W06",
      "source": "perplexity",
      "bajas": [
        {
          "team": "América",
          "player": "Nombre",
          "role": "Delantero",
          "status": "Fuera",
          "impact_level": "High",
          "confidence": 0.82,
          "recency_days": 1,
          "reason": "Lesión muscular"
        }
      ]
    }
    """
    if not os.path.exists(file_path):
        print(f"INFO: {file_path} no encontrado. Se omite integración Perplexity.")
        return team_adjustments

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    bajas = data.get('bajas', [])
    if not isinstance(bajas, list):
        print(f"WARNING: {file_path} tiene formato inválido ('bajas' no es lista).")
        return team_adjustments

    for item in bajas:
        team = dl.canonical_team_name(item.get('team', ''))
        if not team:
            continue

        # Control anti-desactualización y consistencia de plantel actual:
        # - Si Perplexity marca explícitamente que NO está activo para el siguiente partido, se omite.
        # - Si la noticia es vieja (>21 días) y no hay confirmación de vigencia, se omite.
        # - Si el jugador aparece retirado/transferido fuera o con equipo actual distinto, se omite.
        is_active = item.get('is_active_for_next_match', None)
        recency_days = int(item.get('recency_days', 0))

        if is_active is False:
            continue

        if bool(item.get('is_retired', False)):
            continue

        if bool(item.get('is_transferred_out', False)):
            continue

        current_team = dl.canonical_team_name(item.get('current_team', ''))
        if current_team and current_team != team:
            continue

        verification_status = str(item.get('verification_status', 'confirmed')).lower()
        if verification_status in ['stale', 'mismatch', 'unverified']:
            continue

        if recency_days > 21 and is_active is not True:
            continue

        confidence = float(item.get('confidence', 0.75))
        if recency_days > 14 and is_active is not True:
            confidence = min(confidence, 0.55)

        _apply_scaled_adjustment(
            team_adjustments=team_adjustments,
            team_name=team,
            player=item.get('player', 'Unknown'),
            role=item.get('role', ''),
            impact_level=item.get('impact_level', 'Low'),
            status=item.get('status', 'Duda'),
            reason=item.get('reason', ''),
            source='perplexity',
            confidence=confidence,
            recency_days=recency_days,
        )

    return team_adjustments

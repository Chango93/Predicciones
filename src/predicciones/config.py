
# src/predicciones/config.py

import os

def get_config(jornada):
    """
    Genera configuración dinámica por jornada.
    
    Args:
        jornada (int): Número de jornada (1-17)
    
    Returns:
        dict: Configuración completa del modelo
    """
    return {
        'JORNADA': jornada,
        'CURRENT_TOURNAMENT': 'Clausura 2026',
        'PRIOR_TOURNAMENT': 'Apertura 2025',  # Deprecated single
        'PRIOR_TOURNAMENTS': [
            {'name': 'Clausura 2024', 'weight': 0.10},
            {'name': 'Apertura 2024', 'weight': 0.15},
            {'name': 'Clausura 2025', 'weight': 0.25},
            {'name': 'Apertura 2025', 'weight': 0.50},
        ],
        'MAX_JORNADAS_CURRENT': 17,
        'EXPECTED_MATCHES_CURRENT': 153,  # 18 equipos, 17 jornadas, 9 partidos/jornada
        'EXPECTED_TEAMS': 18,
        'SHRINKAGE_DIVISOR_ACTUAL': 18.0,
        'SHRINKAGE_DIVISOR_PROPUESTO': 18.0,
        'W_CURR_MAX': 0.85,
        'BAYES_K': 3.0,
        'BAYES_ALPHA_ATT': 4.0,
        'BAYES_ALPHA_DEF': 5.0,
        'BLEND_K': 6.0,
        'LEAGUE_AVG_K': 30.0,
        'CLAMP_REL_MIN': 0.60,
        'CLAMP_REL_MAX': 1.60,
        'CLAMP_LAMBDA_MIN': 0.25,
        'CLAMP_LAMBDA_MAX': 3.20,
        
        # Dynamic paths based on jornada
        'INPUT_MATCHES': f'data/inputs/jornada_{jornada}_final.json',
        'INPUT_QUALITATIVE': f'data/inputs/Investigacion_cualitativa_jornada{jornada}.json',
        'INPUT_EVALUATION': 'data/inputs/evaluacion_bajas.json',  # Común a todas
        'INPUT_PERPLEXITY_BAJAS': 'data/inputs/perplexity_bajas_semana.json',
        'INPUT_STATS': 'data/inputs/Stats_liga_mx.json',  # Común a todas
        'OUTPUT_CSV': 'outputs/diagnostico_lambda_components.csv',
        'OUTPUT_TXT': 'outputs/diagnostico_report.txt',
    }


def resolve_config(jornada=None):
    """
    Resuelve la configuración activa.

    Precedencia:
    1) Argumento explícito `jornada`
    2) Variable de entorno `PRED_JORNADA`
    3) Fallback a jornada 6
    """
    if jornada is None:
        env_jornada = os.getenv('PRED_JORNADA')
        jornada = int(env_jornada) if env_jornada else 6
    return get_config(int(jornada))

# Backwards compatibility: CONFIG default para J6 (o env si existe)
CONFIG = resolve_config()

# Diccionario de alias EXPLICITOS (mundo real es feo)
CANONICAL_ALIASES = {
    'cf america': 'america',
    'club america': 'america',
    'américa': 'america',
    'pumas': 'pumas',
    'pumas unam': 'pumas',
    'pumas de la unam': 'pumas',
    'unam': 'pumas',
    'queretaro fc': 'queretaro',
    'club queretaro': 'queretaro',
    'querétaro': 'queretaro',
    'tigres uanl': 'tigres',
    'tigres de la uanl': 'tigres',
    'uanl': 'tigres',
    'cd guadalajara': 'guadalajara',
    'club guadalajara': 'guadalajara',
    'fc juarez': 'juarez',
    'atletico san luis': 'atletico de san luis',
    'san luis': 'atletico de san luis',
    'chivas': 'guadalajara',
    'santos': 'santos laguna',
    'leon': 'leon',
}

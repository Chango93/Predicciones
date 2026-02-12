from math import exp, factorial


def poisson_prob(lambda_val, k):
    return (lambda_val**k * exp(-lambda_val)) / factorial(k)


def _captured_mass(lambda_home, lambda_away, max_goals):
    """Masa capturada por la grilla 0..max_goals para ambos equipos."""
    mass_home = sum(poisson_prob(lambda_home, k) for k in range(max_goals + 1))
    mass_away = sum(poisson_prob(lambda_away, k) for k in range(max_goals + 1))
    return mass_home * mass_away


def choose_grid_limit(lambda_home, lambda_away, target_mass=0.995, min_goals=5, max_cap=12):
    """
    Selecciona tamaño de grilla adaptativo para minimizar truncamiento.
def choose_grid_limit(lambda_home, lambda_away, target_mass=0.985, min_goals=5, max_cap=10):
    """
    Selecciona tamaño de grilla adaptativo para evitar truncamiento severo.
    """
    for g in range(min_goals, max_cap + 1):
        if _captured_mass(lambda_home, lambda_away, g) >= target_mass:
            return g
    return max_cap


def optimize_pick_for_quiniela(lambda_home, lambda_away):
    """
    Optimiza pick para scoring de quiniela:
      - 2 pts exacto
      - 1 pt resultado (1/X/2)

    EV(score) = P(resultado del score) + P(exacto score)

    Nota: normaliza probabilidades por la masa capturada en grilla para
    reducir sesgo por truncamiento en lambdas altos.
    """
    max_goals = choose_grid_limit(lambda_home, lambda_away)

    scoreline_probs = []
    prob_home = 0.0
    prob_draw = 0.0
    prob_away = 0.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_prob(lambda_home, h) * poisson_prob(lambda_away, a)
            scoreline_probs.append({'h': h, 'a': a, 'score': f"{h}-{a}", 'prob_raw': p})
            if h > a:
                prob_home += p
            elif h == a:
                prob_draw += p
            else:
                prob_away += p

    captured_mass = prob_home + prob_draw + prob_away
    if captured_mass > 0:
        prob_home /= captured_mass
        prob_draw /= captured_mass
        prob_away /= captured_mass

    for item in scoreline_probs:
        p = item['prob_raw'] / captured_mass if captured_mass > 0 else 0.0
        h, a = item['h'], item['a']

        if h > a:
            p_result = prob_home
            pick_1x2 = '1'
        elif h == a:
            p_result = prob_draw
            pick_1x2 = 'X'
        else:
            p_result = prob_away
            pick_1x2 = '2'

        item['prob'] = p
        item['pick_1x2'] = pick_1x2
        item['ev'] = p_result + p

    score_by_ev = sorted(scoreline_probs, key=lambda x: x['ev'], reverse=True)
    score_by_prob = sorted(scoreline_probs, key=lambda x: x['prob'], reverse=True)
    best = score_by_ev[0]

    confidence_gap = best['ev'] - score_by_ev[1]['ev'] if len(score_by_ev) > 1 else 0.0

    return {
        'pick_exact': best['score'],
        'pick_1x2': best['pick_1x2'],
        'ev': best['ev'],
        'ev_confidence_gap': confidence_gap,
        'prob_home_win': prob_home,
        'prob_draw': prob_draw,
        'prob_away_win': prob_away,
        'top_5_by_prob': score_by_prob[:5],
        'top_5_by_ev': score_by_ev[:5],
        'grid_max_goals': max_goals,
        'captured_mass': captured_mass,
    }

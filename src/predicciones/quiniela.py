from math import exp, factorial


def poisson_prob(lambda_val, k):
    return (lambda_val**k * exp(-lambda_val)) / factorial(k)


def _captured_mass(lambda_home, lambda_away, max_goals):
    """Masa capturada por la grilla 0..max_goals para ambos equipos."""
    mass_home = sum(poisson_prob(lambda_home, k) for k in range(max_goals + 1))
    mass_away = sum(poisson_prob(lambda_away, k) for k in range(max_goals + 1))
    return mass_home * mass_away


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
    """
    max_goals = choose_grid_limit(lambda_home, lambda_away)

    scoreline_probs = []
    prob_home = 0.0
    prob_draw = 0.0
    prob_away = 0.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_prob(lambda_home, h) * poisson_prob(lambda_away, a)
            scoreline_probs.append({'h': h, 'a': a, 'score': f"{h}-{a}", 'prob': p})
            if h > a:
                prob_home += p
            elif h == a:
                prob_draw += p
            else:
                prob_away += p

    for item in scoreline_probs:
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

        item['pick_1x2'] = pick_1x2
        item['ev'] = p_result + item['prob']

    scoreline_probs.sort(key=lambda x: x['ev'], reverse=True)
    best = scoreline_probs[0]

    top_exact = sorted(scoreline_probs, key=lambda x: x['prob'], reverse=True)[:5]

    return {
        'pick_exact': best['score'],
        'pick_1x2': best['pick_1x2'],
        'ev': best['ev'],
        'prob_home_win': prob_home,
        'prob_draw': prob_draw,
        'prob_away_win': prob_away,
        'top_5_scorelines': top_exact,
        'grid_max_goals': max_goals,
        'captured_mass': _captured_mass(lambda_home, lambda_away, max_goals),
    }

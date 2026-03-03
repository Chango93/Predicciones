"""
eval_jornada.py — Evaluación post-jornada
Métricas: ROI real, CLV estimado, Log Loss, Calibration Drift acumulado

Uso: PRED_JORNADA=9 python -m app.steps.eval_jornada
"""

import os
import sys
import json
import math
import csv
from pathlib import Path

JORNADA = int(os.environ.get("PRED_JORNADA", 9))
PRED_CSV = Path(f"outputs/predicciones_jornada_{JORNADA}_final.csv")
RESULTS_JSON = Path(f"data/inputs/resultados_jornada_{JORNADA}.json")
# Histórico de jornadas previas con predicciones en CSV y resultados en historial_usuario.json
HISTORIAL_JSON = Path("data/historial_usuario.json")

HIST_PRED_CSV = {
    6: Path("outputs/predicciones_jornada_6_final.csv"),
    7: Path("outputs/predicciones_jornada_7_final.csv"),
    8: Path("outputs/predicciones_jornada_8_final.csv"),
}

# Cuota implícita de mercado asumida cuando no se proveen closing odds
# Se usa un book genérico de ~105% overround (cuota justa ~1/p * 1.05)
DEFAULT_OVERROUND = 1.05

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def result_from_score(score_home: int, score_away: int) -> str:
    if score_home > score_away:
        return "1"
    elif score_home == score_away:
        return "X"
    else:
        return "2"


def prob_for_outcome(row: dict, outcome: str) -> float:
    mapping = {"1": "prob_home_win", "X": "prob_draw", "2": "prob_away_win"}
    return float(row[mapping[outcome]])


def normalize_odds(odds: dict) -> dict:
    """Elimina overround de cuotas de cierre → probabilidades puras."""
    implied = {k: 1 / v for k, v in odds.items() if v}
    total = sum(implied.values())
    return {k: v / total for k, v in implied.items()}


# ─── Métricas ─────────────────────────────────────────────────────────────────

def compute_log_loss(pred_rows: list[dict], result_map: dict) -> float:
    """
    Log loss = -mean(log(p_actual))
    result_map: {(home, away): '1'|'X'|'2'}
    Sólo partidos con resultado conocido.
    """
    losses = []
    for row in pred_rows:
        key = (row["home_team_canonical"], row["away_team_canonical"])
        outcome = result_map.get(key)
        if outcome is None:
            continue
        p = prob_for_outcome(row, outcome)
        p = max(p, 1e-9)  # clip para evitar log(0)
        losses.append(-math.log(p))
    return sum(losses) / len(losses) if losses else float("nan")


def compute_roi(pred_rows: list[dict], results: list[dict]) -> dict:
    """
    ROI hipotético: 1 unidad por pick con EV>0.5 (picks reales).
    Ganancia = cuota_implicita_modelo - 1 si acierta, -1 si falla.
    Usamos 1/p_pick como cuota implícita justa del modelo.
    """
    units_staked = 0
    profit = 0.0
    correct = 0
    total_picks = 0

    result_map = {
        (r["home"], r["away"]): r["result_1x2"]
        for r in results
        if r["result_1x2"] is not None
    }

    for row in pred_rows:
        pick = row["pick_1x2"]
        if pick == "N/A":
            continue
        key = (row["home_team_canonical"], row["away_team_canonical"])
        outcome = result_map.get(key)
        if outcome is None:
            continue

        total_picks += 1
        units_staked += 1
        p_pick = prob_for_outcome(row, pick)
        implied_cuota = 1 / max(p_pick, 0.01)

        if outcome == pick:
            profit += implied_cuota - 1
            correct += 1
        else:
            profit -= 1

    roi_pct = (profit / units_staked * 100) if units_staked else float("nan")
    return {
        "picks": total_picks,
        "correctos": correct,
        "tasa_acierto": correct / total_picks if total_picks else 0,
        "profit_units": round(profit, 3),
        "roi_pct": round(roi_pct, 2),
    }


def compute_clv(pred_rows: list[dict], results: list[dict]) -> dict:
    """
    CLV (Closing Line Value) por pick con resultado conocido.
    CLV% = (p_modelo - p_closing_justa) / p_closing_justa × 100
    Positivo = el modelo identificó valor vs mercado de cierre.
    Si no hay closing odds, se estima un overround de 105%.
    """
    clv_values = []
    has_closing = False

    result_map = {(r["home"], r["away"]): r for r in results if r["result_1x2"]}

    for row in pred_rows:
        pick = row["pick_1x2"]
        if pick == "N/A":
            continue
        key = (row["home_team_canonical"], row["away_team_canonical"])
        rdata = result_map.get(key)
        if rdata is None:
            continue

        p_model = prob_for_outcome(row, pick)
        closing = rdata.get("closing_odds", {})

        if closing and all(closing.get(k) for k in ("1", "X", "2")):
            has_closing = True
            probs_closing = normalize_odds({k: float(v) for k, v in closing.items()})
            p_closing = probs_closing[pick]
        else:
            # Sin cuota de cierre: usamos la propia cuota del modelo con overround para simular mercado
            p_closing = p_model / DEFAULT_OVERROUND

        clv_pct = (p_model - p_closing) / max(p_closing, 0.01) * 100
        clv_values.append({
            "match": f"{row['home_team_canonical']} vs {row['away_team_canonical']}",
            "pick": pick,
            "p_model": round(p_model, 3),
            "p_closing": round(p_closing, 3),
            "clv_pct": round(clv_pct, 2),
        })

    mean_clv = sum(v["clv_pct"] for v in clv_values) / len(clv_values) if clv_values else 0
    return {
        "has_real_closing_odds": has_closing,
        "mean_clv_pct": round(mean_clv, 2),
        "por_partido": clv_values,
    }


def compute_calibration(jornada_data: list[dict]) -> dict:
    """
    Calibration drift acumulado sobre todas las jornadas disponibles.
    jornada_data: lista de {p_predicted, outcome_bool}
    ECE = mean(|p_bin - freq_bin|) ponderado por tamaño de bin.
    """
    if not jornada_data:
        return {"ece": float("nan"), "bins": []}

    bins = [(i/10, (i+1)/10) for i in range(10)]
    bin_data = []

    for lo, hi in bins:
        bucket = [d for d in jornada_data if lo <= d["p"] < hi]
        if not bucket:
            continue
        mean_p = sum(d["p"] for d in bucket) / len(bucket)
        freq = sum(1 for d in bucket if d["hit"]) / len(bucket)
        weight = len(bucket) / len(jornada_data)
        bin_data.append({
            "rango": f"{lo:.1f}-{hi:.1f}",
            "n": len(bucket),
            "p_media": round(mean_p, 3),
            "freq_real": round(freq, 3),
            "drift": round(abs(mean_p - freq), 3),
            "peso": round(weight, 3),
        })

    ece = sum(b["drift"] * b["peso"] for b in bin_data)
    return {"ece": round(ece, 4), "bins": bin_data}


def build_calibration_dataset(current_pred_rows, current_results):
    """
    Agrega predicciones históricas (J6-J8) + jornada actual para calibración acumulada.
    Cada punto = {p: float, hit: bool} para CADA partido y CADA resultado (1,X,2).
    """
    data_points = []

    # Histórico desde historial_usuario.json + CSVs de predicciones
    with open(HISTORIAL_JSON, encoding="utf-8") as f:
        historial = json.load(f)["history"]

    for entry in historial:
        j = entry["jornada"]
        csv_path = HIST_PRED_CSV.get(j)
        if not csv_path or not csv_path.exists():
            continue

        pred_rows_hist = load_csv(csv_path)
        # Construir mapa de resultados del historial
        result_map_hist = {}
        for m in entry["matches"]:
            # resultado real del score
            pred_score = m["prediction"].split("-")
            real_score = m["result"].split("-")
            if len(real_score) == 2:
                try:
                    sh, sa = int(real_score[0]), int(real_score[1])
                    result_map_hist[(
                        m["home"].lower().strip(),
                        m["away"].lower().strip()
                    )] = result_from_score(sh, sa)
                except ValueError:
                    pass

        for row in pred_rows_hist:
            key = (row["home_team_canonical"], row["away_team_canonical"])
            outcome = result_map_hist.get(key)
            if outcome is None:
                continue
            for o in ("1", "X", "2"):
                data_points.append({
                    "p": prob_for_outcome(row, o),
                    "hit": (outcome == o),
                })

    # Jornada actual
    result_map_curr = {
        (r["home"], r["away"]): r["result_1x2"]
        for r in current_results
        if r["result_1x2"] is not None
    }
    for row in current_pred_rows:
        key = (row["home_team_canonical"], row["away_team_canonical"])
        outcome = result_map_curr.get(key)
        if outcome is None:
            continue
        for o in ("1", "X", "2"):
            data_points.append({
                "p": prob_for_outcome(row, o),
                "hit": (outcome == o),
            })

    return data_points


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  EVALUACIÓN POST-JORNADA {JORNADA} — Clausura 2026")
    print(f"{'='*60}")

    if not PRED_CSV.exists():
        print(f"[ERROR] No encontré {PRED_CSV}")
        sys.exit(1)
    if not RESULTS_JSON.exists():
        print(f"[ERROR] No encontré {RESULTS_JSON}")
        print(f"  → Llena el template en data/inputs/resultados_jornada_{JORNADA}.json")
        sys.exit(1)

    pred_rows = load_csv(PRED_CSV)

    with open(RESULTS_JSON, encoding="utf-8") as f:
        results_data = json.load(f)
    results = results_data["matches"]

    # Validar que hay resultados
    filled = [r for r in results if r["result_1x2"] is not None]
    if not filled:
        print("[ERROR] El archivo de resultados está vacío (todos null).")
        print(f"  → Llena data/inputs/resultados_jornada_{JORNADA}.json con los marcadores reales.")
        sys.exit(1)

    print(f"\n  Partidos con resultado: {len(filled)}/{len(results)}")

    result_map = {(r["home"], r["away"]): r["result_1x2"] for r in filled}

    # ── Log Loss ──────────────────────────────────────────────────────────────
    ll = compute_log_loss(pred_rows, result_map)
    print(f"\n{'─'*60}")
    print(f"  LOG LOSS (J{JORNADA}): {ll:.4f}")
    print(f"  Referencia: modelo naive (33.3% cada resultado) = {-math.log(1/3):.4f}")
    skill_vs_naive = (-math.log(1/3) - ll) / (-math.log(1/3)) * 100
    print(f"  Skill Score vs naive: {skill_vs_naive:+.1f}%  {'✓ MEJOR que azar' if skill_vs_naive > 0 else '✗ PEOR que azar'}")

    # ── ROI ───────────────────────────────────────────────────────────────────
    roi = compute_roi(pred_rows, results)
    print(f"\n{'─'*60}")
    print(f"  ROI REAL (J{JORNADA})")
    print(f"  Picks con resultado: {roi['picks']}")
    print(f"  Correctos: {roi['correctos']} ({roi['tasa_acierto']*100:.1f}%)")
    print(f"  Profit hipotético: {roi['profit_units']:+.3f} units")
    print(f"  ROI: {roi['roi_pct']:+.2f}%")

    # ── CLV ───────────────────────────────────────────────────────────────────
    clv = compute_clv(pred_rows, results)
    print(f"\n{'─'*60}")
    print(f"  CLV ESTIMADO (J{JORNADA})")
    if not clv["has_real_closing_odds"]:
        print(f"  [!] Sin cuotas de cierre reales → CLV estimado con overround {DEFAULT_OVERROUND:.0%}")
    print(f"  CLV medio: {clv['mean_clv_pct']:+.2f}%")
    print(f"\n  {'Partido':<35} {'Pick':^4} {'p_modelo':^9} {'p_cierre':^9} {'CLV%':^7}")
    print(f"  {'─'*35} {'─'*4} {'─'*9} {'─'*9} {'─'*7}")
    for v in clv["por_partido"]:
        sign = "+" if v["clv_pct"] >= 0 else ""
        print(f"  {v['match']:<35} {v['pick']:^4} {v['p_model']:^9.3f} {v['p_closing']:^9.3f} {sign}{v['clv_pct']:^6.1f}%")

    # ── Calibration Drift ─────────────────────────────────────────────────────
    calib_data = build_calibration_dataset(pred_rows, results)
    calib = compute_calibration(calib_data)
    print(f"\n{'─'*60}")
    print(f"  CALIBRATION DRIFT ACUMULADO (J6→J{JORNADA})")
    print(f"  ECE (Expected Calibration Error): {calib['ece']:.4f}")
    print(f"  Referencia: ECE < 0.05 = bien calibrado | ECE > 0.10 = problemático")
    print(f"\n  {'Bin':^10} {'N':^5} {'p̄_pred':^8} {'f_real':^8} {'drift':^8} {'peso':^6}")
    print(f"  {'─'*10} {'─'*5} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")
    for b in calib["bins"]:
        flag = " ← !" if b["drift"] > 0.10 else ""
        print(f"  {b['rango']:^10} {b['n']:^5} {b['p_media']:^8.3f} {b['freq_real']:^8.3f} {b['drift']:^8.3f} {b['peso']:^6.3f}{flag}")

    # ── Guardar JSON ──────────────────────────────────────────────────────────
    out = {
        "jornada": JORNADA,
        "log_loss": round(ll, 4),
        "log_loss_naive": round(-math.log(1/3), 4),
        "skill_score_pct": round(skill_vs_naive, 2),
        "roi": roi,
        "clv": clv,
        "calibration": calib,
    }
    out_path = Path(f"outputs/evaluacion_jornada_{JORNADA}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n{'─'*60}")
    print(f"  Reporte guardado: {out_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

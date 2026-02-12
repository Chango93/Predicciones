# Prompt para Perplexity (bajas semanales)

Copia y pega este prompt en Perplexity para generar el archivo que consume el modelo.

---

Necesito un reporte **estructurado en JSON puro** (sin texto adicional, sin markdown) sobre bajas de Liga MX para la semana actual.

Objetivo: usarlo en un modelo de predicción de quiniela.

## Reglas
1. Devuelve **solo JSON válido**.
2. Incluye solo jugadores de **impacto real** para el partido de esta semana.
3. Si hay duda, usa `status: "Duda"` y `confidence` más baja.
4. `confidence` debe estar entre `0.30` y `1.00`.
5. `recency_days` = días transcurridos desde la noticia/confirmación principal.
6. `impact_level` solo puede ser: `High`, `Mid`, `Low`.
7. `role` solo puede ser uno de: `Portero`, `Defensa`, `Mediocampista`, `Delantero`.
8. Equipos en español (ej. "América", "Pumas", "Cruz Azul").

## Formato exacto esperado
{
  "week_reference": "2026-W06",
  "source": "perplexity",
  "generated_at": "2026-02-12T12:00:00Z",
  "bajas": [
    {
      "team": "América",
      "player": "Jugador Ejemplo",
      "role": "Delantero",
      "status": "Fuera",
      "impact_level": "High",
      "confidence": 0.86,
      "recency_days": 1,
      "reason": "Lesión muscular",
      "evidence": "URL o fuente breve"
    }
  ]
}

## Cobertura
Incluye solo equipos de Liga MX y jugadores con impacto probable en la próxima jornada.

---

## Cómo guardarlo
Guardar el resultado como:

`data/inputs/perplexity_bajas_semana.json`

Así el pipeline lo integra automáticamente.

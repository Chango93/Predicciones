# Prompt para Perplexity (bajas semanales, usando imagen del fixture y control anti-desactualización)

Copia y pega este prompt en Perplexity y adjunta la imagen del fixture de la jornada.

---

Te voy a adjuntar una **imagen del fixture de la jornada** de Liga MX.
Necesito que generes un reporte de bajas **en JSON puro** (sin texto adicional, sin markdown) para alimentar un modelo de predicción.

## Objetivo
Incluir solo bajas vigentes y jugadores correctos para los partidos de la jornada mostrada en la imagen.

## Reglas críticas (obligatorias)
1. Usa la imagen para identificar **solo equipos que sí juegan esta jornada**.
2. Incluye solo jugadores de esos equipos.
3. Verifica que el jugador **sigue en ese club actualmente** (no retirado, no transferido a otro club).
4. Si un jugador está retirado o en otro equipo: **NO incluirlo**.
5. Excluye noticias viejas/no confirmadas.
6. Si una noticia tiene más de 21 días sin confirmación reciente, no la incluyas.
7. Si no puedes confirmar vigencia para el siguiente partido, marca `is_active_for_next_match: false`.

## Verificación mínima requerida por registro
- Debe tener al menos una fuente confiable reciente.
- Debe incluir:
  - `last_verified_at` (ISO datetime)
  - `is_active_for_next_match` (true/false)
  - `current_team`
  - `is_retired` (true/false)
  - `is_transferred_out` (true/false)
  - `verification_status` (`confirmed` | `unverified` | `stale` | `mismatch`)

## Reglas de formato
1. Devuelve **solo JSON válido**.
2. `confidence` entre `0.30` y `1.00`.
3. `impact_level`: `High`, `Mid`, `Low`.
4. `role`: `Portero`, `Defensa`, `Mediocampista`, `Delantero`.
5. Equipos en español (ej. "América", "Pumas", "Cruz Azul").

## Formato exacto esperado
{
  "week_reference": "2026-W06",
  "source": "perplexity",
  "generated_at": "2026-02-12T12:00:00Z",
  "bajas": [
    {
      "team": "Tigres",
      "current_team": "Tigres",
      "player": "Jugador Ejemplo",
      "role": "Delantero",
      "status": "Fuera",
      "impact_level": "High",
      "confidence": 0.86,
      "recency_days": 1,
      "is_active_for_next_match": true,
      "is_retired": false,
      "is_transferred_out": false,
      "verification_status": "confirmed",
      "last_verified_at": "2026-02-12T09:30:00Z",
      "reason": "Lesión muscular",
      "evidence": "https://..."
    }
  ]
}

## Salida final
Entrega **únicamente** el JSON.

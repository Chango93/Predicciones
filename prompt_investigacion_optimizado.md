# Template de Investigación Cualitativa (Perplexity)

**ROL:** Investigador Deportivo Senior (Liga MX)
**OBJETIVO:** Encontrar **Contexto Crítico** (Lesiones, Transferencias, Noticias) para los partidos listados.
**NO CALCULAR:** No busques estadísticas, tablas, ni goles. Esos datos ya los tengo.
**TU MISIÓN:** Llenar los vacíos cualitativos del JSON.

## INSTRUCCIONES PARA PERPLEXITY

Copia y pega la lista de partidos de abajo. Para CADA partido, busca y reporta en formato JSON limpio:
1.  **AUSENCIAS (Absences):**
    *   Lesiones confirmadas de jugadores **TITULARES o CLAVE**.
    *   Suspensiones recientes.
    *   *Formato:* `name`, `role`, `status` (fuera/duda), `importance` (alta/media), `reason`.
2.  **ALTAS Y BAJAS (Roster Changes):**
    *   fichajes CONFIRMADOS (`transfer_in`) o salidas (`transfer_out`) en los últimos 7 días.
    *   Solo jugadores relevantes.
3.  **CONTEXTO COMPETITIVO:**
    *   ¿Hay presión extrema sobre el técnico?
    *   ¿Juegan con suplentes por otro torneo (Concacaf)?
    *   ¿Problemas extra-cancha graves?

---

## ESTRUCTURA DE RESPUESTA REQUERIDA (JSON)

Por favor devuelve SOLO un array JSON con los objetos de actualización para cada partido:

```json
[
  {
    "match_id": "HomeTeam vs AwayTeam",
    "absences": {
      "home": [
        { 
          "name": "Jugador X", 
          "role": "atacante", 
          "status": "fuera", 
          "importance": "alta", 
          "reason": "lesion rodilla", 
          "evidence_level": "medio_top",
          "source_url": "url" 
        }
      ],
      "away": []
    },
    "roster_changes": {
      "home": [],
      "away": [
        { 
          "name": "Refuerzo Y", 
          "type": "transfer_in", 
          "role": "defensor", 
          "importance": "media", 
          "evidence_level": "medio_top",
          "source_url": "url" 
        }
      ]
    },
    "competitive_context": [
      { 
        "type": "pressure", 
        "team": "home",
        "claim": "DT en riesgo de despido si pierde", 
        "evidence_level": "medio_top"
      },
      { 
        "type": "concacaf_load", 
        "team": "away",
        "claim": "Equipo visitante jugará Concachampions el miércoles", 
        "evidence_level": "alto_confirmado"
      }
    ],
    "pitch_notes": "Si encuentras info sobre el estado de la cancha (lluvia/malo)"
  }
]
```

## ⚠️ CAMPOS OBLIGATORIOS (CRÍTICO)

- `absences`: Cada item DEBE tener `"evidence_level"` (valores: `"oficial_club"`, `"medio_top"`, `"stats_db_top"`, `"alto_confirmado"`, `"medio_declaraciones"`)
- `roster_changes`: Cada item DEBE tener `"evidence_level"` (mismos valores)

### 🚨 CAMPO TEAM EN COMPETITIVE_CONTEXT (SUPER IMPORTANTE)

**CADA item en competitive_context DEBE incluir `"team": "home"` o `"team": "away"`**

Esto indica QUÉ EQUIPO es afectado por la situación. Ejemplos:

| Situación | team | Razón |
|-----------|------|-------|
| "Tigres jugará Concachampions" (Tigres es local) | `"home"` | Afecta al equipo LOCAL |
| "Chivas líder invicto" (Chivas es visita vs Mazatlán) | `"away"` | Afecta al equipo VISITANTE |
| "DT de América bajo presión" (América es local) | `"home"` | Afecta al equipo LOCAL |
| "Monterrey sin 3 titulares" (Monterrey es visita) | `"away"` | Afecta al equipo VISITANTE |

**SI OMITES EL CAMPO `team`, EL AJUSTE NO SE APLICARÁ AL MODELO.**


## LISTA DE PARTIDOS A INVESTIGAR
*Jornada 5 de liga mx clausura 2026*


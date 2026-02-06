# 🔢 Reporte Técnico: Optimización Quiniela (EV)

**Generado:** 2026-02-06T00:49:54.217793
**Estrategia:** Maximizar Puntos (2pts Exacto / 1pt Resultado)
**Fórmula EV:** Prob. Exacta + Prob. Resultado

---

## Tigres vs. Santos Laguna
### 🗞️ Contexto y Novedades
- ℹ️ **SUSPENSION_KEY_PLAYER:** Gignac suspendido por primera vez en su carrera en Liga MX (428 partidos), Tigres pierde a su máximo referente ofensivo *(info, no ajusta modelo)*
- ℹ️ **FORM:** Santos sin victorias en todo el torneo, penúltimo lugar del campeonato *(info, no ajusta modelo)*

**Movimientos de Mercado:**
- 🔴 **BAJA (Tigres):** Uriel Antuna (extremo)
- 🟢 **ALTA (Santos Laguna):** Lucas Dillorio (delantero)
- 🟢 **ALTA (Santos Laguna):** Carlos Gruezo (volante)
- 🟢 **ALTA (Santos Laguna):** Efraín Orona (defensor central)

**Ausencias Relevantes:**
- 🚑 Baja **(Tigres):** André-Pierre Gignac - *suspensión (primera tarjeta roja en 428 partidos, doble amarilla vs León)*
- 🚑 Baja **(Tigres):** Marco Farfán - *fractura escafoides pie derecho, operado, recuperación hasta marzo*
- 🚑 Baja **(Santos Laguna):** Anthony 'Choco' Lozano - *lesión ligamento cruzado anterior, no registrado para Clausura 2026*
- 🚑 Baja **(Santos Laguna):** Bruno Barticciotto - *lesiones recurrentes, regreso a Talleres de Córdoba*

### 🧪 Análisis de Lambdas (Goles Esperados)
**Tigres (Local) = 2.4556**
- *Fuerza Ataque*: 1.172 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 1.333
- *Media Liga Local*: 1.81
- *Cálculo Base*: 1.172 * 1.333 * 1.81 = 2.829

**Santos Laguna (Visita) = 0.4603**
- *Fuerza Ataque*: 0.718 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.562
- *Media Liga Visita*: 1.29
- *Cálculo Base*: 0.718 * 0.562 * 1.29 = 0.52

**📊 Desglose Completo de Ajustes:**
```
Tigres (Local):
  λ_base  = 2.8287
  [HOME] [-12.0%] Reducción Lambda Propio (12%) por baja Goleador Top: André-Pierre Gignac
  [HOME] [-1.3%] Reducción Lambda Propio (9%) por BAJA/Transferencia Atacante (Pond. Hist: 15%): Uriel Antuna
  λ_final = 2.4556
  Impacto Total: -13.2%

Santos Laguna (Visita):
  λ_base  = 0.5205
  [AWAY] [+6.0%] Aumento Lambda Rival (6%) por baja Defensor (→ Beneficia Santos Laguna): Marco Farfán
  [AWAY] [-9.0%] Reducción Lambda Propio (9%) por baja Atacante: Anthony 'Choco' Lozano
  [AWAY] [-9.0%] Reducción Lambda Propio (9%) por baja Atacante: Bruno Barticciotto
  [AWAY] [+0.8%] BOOST Lambda Propio (5%) por Fichaje Goleador Top (Pond. Hist: 15%, Adapt: 100%): Lucas Dillorio
  λ_final = 0.4603
  Impacto Total: -11.6%
```

**🔍 Interpretación:**
- Los ajustes DISMINUYÓ significativamente (-13.2%) los goles esperados de Tigres
- Los ajustes DISMINUYÓ significativamente (-11.6%) los goles esperados de Santos Laguna
- Esto modifica las probabilidades de resultado y marcador final

**Probabilidades Generales:** Local 80.6% | Empate 15.1% | Visita 4.3%

### 🎯 Mejores Opciones (Ranking por Valor Esperado)
| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |
| :--- | :--- | :--- | :--- | :--- |
| **2-0** | HOME | 16.3% | 80.6% | **1.009** |
| 3-0 | HOME | 13.4% | 80.6% | 0.979 |
| 1-0 | HOME | 12.5% | 80.6% | 0.971 |
| 4-0 | HOME | 8.2% | 80.6% | 0.928 |
| 2-1 | HOME | 7.5% | 80.6% | 0.881 |
| 3-1 | HOME | 6.2% | 80.6% | 0.867 |
| 0-0 | DRAW | 6.2% | 15.1% | 0.233 |
| 1-1 | DRAW | 6.9% | 15.1% | 0.220 |

## Necaxa vs. Atletico de San Luis
### 🗞️ Contexto y Novedades
- ℹ️ **FORM:** Necaxa con solo un triunfo en el torneo, viene de tres derrotas consecutivas *(info, no ajusta modelo)*
- ℹ️ **FORM:** San Luis también solo tiene un triunfo en el certamen *(info, no ajusta modelo)*

**Movimientos de Mercado:**
- 🔴 **BAJA (Necaxa):** Johan Rojas (mediocampista)
- 🔴 **BAJA (Necaxa):** José Iván Rodríguez (mediocampista)

**Ausencias Relevantes:**
- 🚑 Baja **(Necaxa):** Kevin Gutiérrez - *suspensión por expulsión vs América (doble amarilla)*

### 🧪 Análisis de Lambdas (Goles Esperados)
**Necaxa (Local) = 0.8890**
- *Fuerza Ataque*: 0.653 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.848
- *Media Liga Local*: 1.81
- *Cálculo Base*: 0.653 * 0.848 * 1.81 = 1.003

**Atletico de San Luis (Visita) = 1.3893**
- *Fuerza Ataque*: 1.28 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.841
- *Media Liga Visita*: 1.29
- *Cálculo Base*: 1.28 * 0.841 * 1.29 = 1.389

**📊 Desglose Completo de Ajustes:**
```
Necaxa (Local):
  λ_base  = 1.0028
  [HOME] [-10.0%] Reducción Lambda Propio (10%) por baja Creativo Top: Kevin Gutiérrez
  [HOME] [-0.8%] Reducción Lambda Propio (5%) por BAJA/Transferencia Mediocampista (Pond. Hist: 15%): Johan Rojas
  [HOME] [-0.8%] Reducción Lambda Propio (5%) por BAJA/Transferencia Mediocampista (Pond. Hist: 15%): José Iván Rodríguez
  λ_final = 0.8890
  Impacto Total: -11.3%

Atletico de San Luis (Visita):
  λ_base  = 1.3893
  λ_final = 1.3893
  Impacto Total: +0.0%
```

**🔍 Interpretación:**
- Los ajustes DISMINUYÓ significativamente (-11.3%) los goles esperados de Necaxa
- Esto modifica las probabilidades de resultado y marcador final

**Probabilidades Generales:** Local 22.4% | Empate 30.7% | Visita 46.9%

### 🎯 Mejores Opciones (Ranking por Valor Esperado)
| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |
| :--- | :--- | :--- | :--- | :--- |
| **0-1** | AWAY | 12.6% | 46.9% | **0.635** |
| 0-2 | AWAY | 9.9% | 46.9% | 0.608 |
| 1-2 | AWAY | 8.8% | 46.9% | 0.557 |
| 0-3 | AWAY | 4.6% | 46.9% | 0.555 |
| 1-1 | DRAW | 14.3% | 30.7% | 0.450 |
| 0-0 | DRAW | 11.9% | 30.7% | 0.446 |
| 1-0 | HOME | 7.5% | 22.4% | 0.299 |
| 2-1 | HOME | 5.6% | 22.4% | 0.280 |

## Tijuana vs. Puebla
### 🗞️ Contexto y Novedades
- ℹ️ **INJURY_KEY_PLAYER:** Tijuana sin Gilberto Mora, su estrella y referente ofensivo, desde hace dos semanas. Solo tienen un triunfo con él fuera *(info, no ajusta modelo)*
- ℹ️ **FORM:** Puebla no termina por levantar en el torneo, solo tiene 4 puntos *(info, no ajusta modelo)*

**Movimientos de Mercado:**
- 🔴 **BAJA (Puebla):** Efraín Orona (defensor)
- 🔴 **BAJA (Puebla):** Ricardo Marín (delantero)

**Ausencias Relevantes:**
- 🚑 Baja **(Tijuana):** Gilberto Mora - *pubalgia, 4-6 semanas fuera (desde 21 enero), referente del equipo*
- 🚑 Baja **(Puebla):** Nicolás Díaz - *suspensión*

### 🧪 Análisis de Lambdas (Goles Esperados)
**Tijuana (Local) = 2.7928**
- *Fuerza Ataque*: 1.104 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 1.306
- *Media Liga Local*: 1.81
- *Cálculo Base*: 1.104 * 1.306 * 1.81 = 2.611

**Puebla (Visita) = 0.4905**
- *Fuerza Ataque*: 0.719 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.536
- *Media Liga Visita*: 1.29
- *Cálculo Base*: 0.719 * 0.536 * 1.29 = 0.497

**📊 Desglose Completo de Ajustes:**
```
Tijuana (Local):
  λ_base  = 2.6112
  [HOME] [+6.0%] Aumento Lambda Rival (6%) por baja Defensor (→ Beneficia Tijuana): Nicolás Díaz
  [HOME] [+0.9%] Aumento Lambda Rival (6%) por BAJA/Transferencia Defensor (Pond. Hist: 15%) (→ Beneficia Tijuana): Efraín Orona
  λ_final = 2.7928
  Impacto Total: +7.0%

Puebla (Visita):
  λ_base  = 0.4972
  [AWAY] [-1.3%] Reducción Lambda Propio (9%) por BAJA/Transferencia Atacante (Pond. Hist: 15%): Ricardo Marín
  λ_final = 0.4905
  Impacto Total: -1.3%
```

**🔍 Interpretación:**
- Esto modifica las probabilidades de resultado y marcador final

**Probabilidades Generales:** Local 84.2% | Empate 12.3% | Visita 3.6%

### 🎯 Mejores Opciones (Ranking por Valor Esperado)
| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |
| :--- | :--- | :--- | :--- | :--- |
| **2-0** | HOME | 14.6% | 84.2% | **1.028** |
| 3-0 | HOME | 13.6% | 84.2% | 1.018 |
| 1-0 | HOME | 9.8% | 84.2% | 0.980 |
| 4-0 | HOME | 9.5% | 84.2% | 0.977 |
| 5-0 | HOME | 5.3% | 84.2% | 0.935 |
| 2-1 | HOME | 7.2% | 84.2% | 0.913 |
| 3-1 | HOME | 6.7% | 84.2% | 0.908 |
| 1-1 | DRAW | 5.8% | 12.3% | 0.181 |

## Mazatlán vs. CD Guadalajara
### 🗞️ Contexto y Novedades
- ℹ️ **DESPEDIDA_ESTADIO:** Última temporada de Mazatlán en Liga MX: franquicia vendida a Atlante, se muda a CDMX en junio 2026. Despedida del Estadio El Encanto *(info, no ajusta modelo)*
- ℹ️ **INVICTO_LIDER:** Chivas líder absoluto con paso perfecto: 4 victorias en 4 partidos, invicto. Último arranque similar fue en Bicentenario 2010 (hace 16 años) *(info, no ajusta modelo)*
- ℹ️ **FORM:** Mazatlán ha perdido todos sus puntos en el torneo, sin victorias. Diferencias inconmensurables con Chivas *(info, no ajusta modelo)*

**Ausencias Relevantes:**
- ⚠️ Duda **(Mazatlán):** Fábio Gomes - *lesión muscular*
- 🚑 Baja **(CD Guadalajara):** Diego Campillo - *fractura en el pie, recuperación hasta finales de enero*

- 🏟️ *Última visita de Chivas al Estadio El Encanto (antes Kraken) en Mazatlán*

### 🧪 Análisis de Lambdas (Goles Esperados)
**Mazatlán (Local) = 1.0465**
- *Fuerza Ataque*: 0.84 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.68
- *Media Liga Local*: 1.81
- *Cálculo Base*: 0.84 * 0.68 * 1.81 = 1.034

**CD Guadalajara (Visita) = 2.2360**
- *Fuerza Ataque*: 1.124 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 1.543
- *Media Liga Visita*: 1.29
- *Cálculo Base*: 1.124 * 1.543 * 1.29 = 2.236

**📊 Desglose Completo de Ajustes:**
```
Mazatlán (Local):
  λ_base  = 1.0338
  [HOME] [-4.5%] Reducción Lambda Propio (9%) por baja Atacante (Duda: 50% efecto): Fábio Gomes
  [HOME] [+6.0%] Aumento Lambda Rival (6%) por baja Defensor (→ Beneficia Mazatlán): Diego Campillo
  λ_final = 1.0465
  Impacto Total: +1.2%

CD Guadalajara (Visita):
  λ_base  = 2.2360
  λ_final = 2.2360
  Impacto Total: +0.0%
```

**Probabilidades Generales:** Local 15.4% | Empate 21.5% | Visita 63.1%

### 🎯 Mejores Opciones (Ranking por Valor Esperado)
| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |
| :--- | :--- | :--- | :--- | :--- |
| **1-2** | AWAY | 9.8% | 63.1% | **0.729** |
| 0-2 | AWAY | 9.4% | 63.1% | 0.725 |
| 1-3 | AWAY | 7.3% | 63.1% | 0.704 |
| 0-1 | AWAY | 7.2% | 63.1% | 0.704 |
| 0-3 | AWAY | 7.0% | 63.1% | 0.701 |
| 1-1 | DRAW | 9.9% | 21.5% | 0.314 |
| 2-2 | DRAW | 5.1% | 21.5% | 0.267 |
| 0-0 | DRAW | 4.9% | 21.5% | 0.264 |

## Queretaro FC vs. León
### 🗞️ Contexto y Novedades
- ℹ️ **FORM:** Querétaro sin poder levantar en el torneo, busca su primer triunfo. Dueños cuestionados desde hace varios torneos *(info, no ajusta modelo)*
- ℹ️ **FORM:** León no termina por acomodarse con Ignacio Ambriz como DT *(info, no ajusta modelo)*

**Ausencias Relevantes:**
- 🚑 Baja **(Queretaro FC):** Santiago Homenchenko - *suspensión*
- 🚑 Baja **(Queretaro FC):** Diego Reyes - *lesión muscular, regreso estimado finales de febrero*
- 🚑 Baja **(León):** Nicolás Vallejo - *desgarro, perdió primeras 3 jornadas, posible regreso próximamente*

### 🧪 Análisis de Lambdas (Goles Esperados)
**Queretaro FC (Local) = 1.4087**
- *Fuerza Ataque*: 0.734 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 1.116
- *Media Liga Local*: 1.81
- *Cálculo Base*: 0.734 * 1.116 * 1.81 = 1.483

**León (Visita) = 0.4500**
- *Fuerza Ataque*: 0.343 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 1.117
- *Media Liga Visita*: 1.29
- *Cálculo Base*: 0.343 * 1.117 * 1.29 = 0.495

**📊 Desglose Completo de Ajustes:**
```
Queretaro FC (Local):
  λ_base  = 1.4829
  [HOME] [-5.0%] Reducción Lambda Propio (5%) por baja Mediocampista: Santiago Homenchenko
  λ_final = 1.4087
  Impacto Total: -5.0%

León (Visita):
  λ_base  = 0.4946
  [AWAY] [-9.0%] Reducción Lambda Propio (9%) por baja Atacante: Nicolás Vallejo
  λ_final = 0.4500
  Impacto Total: -9.0%
```

**🔍 Interpretación:**
- Esto modifica las probabilidades de resultado y marcador final

**Probabilidades Generales:** Local 59.8% | Empate 29.7% | Visita 10.4%

### 🎯 Mejores Opciones (Ranking por Valor Esperado)
| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |
| :--- | :--- | :--- | :--- | :--- |
| **1-0** | HOME | 20.7% | 59.8% | **0.825** |
| 2-0 | HOME | 15.5% | 59.8% | 0.773 |
| 3-0 | HOME | 7.3% | 59.8% | 0.691 |
| 2-1 | HOME | 7.0% | 59.8% | 0.668 |
| 3-1 | HOME | 3.3% | 59.8% | 0.631 |
| 0-0 | DRAW | 16.9% | 29.7% | 0.486 |
| 1-1 | DRAW | 11.2% | 29.7% | 0.409 |
| 0-1 | AWAY | 5.7% | 10.4% | 0.162 |

## Toluca vs. Cruz Azul
### 🗞️ Contexto y Novedades
- ℹ️ **CRISIS_DELANTEROS:** Cruz Azul sin delantero centro: Ángel Sepúlveda vendido a Chivas, Toro Fernández suspendido 2 partidos + lesionado. Mateo Levy única opción disponible *(info, no ajusta modelo)*
- ℹ️ **DT_SUSPENDIDO:** Nicolás Larcamón suspendido 1 partido, no estará en el banquillo. Su auxiliar Javier Omar Berges también suspendido 2 partidos *(info, no ajusta modelo)*
- ℹ️ **HISTORY:** Toluca no le gana a Cruz Azul desde julio de 2023. Duelo parejo: Toluca invicto y Cruz Azul con 3 victorias consecutivas *(info, no ajusta modelo)*

**Movimientos de Mercado:**
- 🔴 **BAJA (Cruz Azul):** Ángel Sepúlveda (delantero centro)

**Ausencias Relevantes:**
- 🚑 Baja **(Toluca):** Alexis Vega - *lesión de rodilla, regreso mediados de febrero 2026*
- ⚠️ Duda **(Toluca):** Helinho ⭐ Top-40 (Rating: 7.20) - *lesión por distensión*
- 🚑 Baja **(Cruz Azul):** Gabriel 'Toro' Fernández - *suspensión 2 partidos por expulsión vs Juárez + lesión tobillo vs Vancouver*
- 🚑 Baja **(Cruz Azul):** Kevin Mier - *fractura de tibia en rodilla, 6-10 meses fuera*
- 🚑 Baja **(Cruz Azul):** Andrés Montaño - *ruptura ligamento cruzado anterior, fuera todo el torneo*
- 🚑 Baja **(Cruz Azul):** Willer Ditta - *suspensión*

### 🧪 Análisis de Lambdas (Goles Esperados)
**Toluca (Local) = 2.0023**
- *Fuerza Ataque*: 1.509 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.701
- *Media Liga Local*: 1.81
- *Cálculo Base*: 1.509 * 0.701 * 1.81 = 1.914

**Cruz Azul (Visita) = 1.3718**
- *Fuerza Ataque*: 1.225 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.913
- *Media Liga Visita*: 1.29
- *Cálculo Base*: 1.225 * 0.913 * 1.29 = 1.444

**📊 Desglose Completo de Ajustes:**
```
Toluca (Local):
  λ_base  = 1.9144
  [HOME] [-12.0%] Reducción Lambda Propio (12%) por baja Goleador Top: Alexis Vega
  [HOME] [-2.5%] Reducción Lambda Propio (5%) por baja Mediocampista (Duda: 50% efecto): Helinho
  [HOME] [+15.0%] Aumento Lambda Rival (15%) por baja Portero Titular (→ Beneficia Toluca): Kevin Mier
  [HOME] [+6.0%] Aumento Lambda Rival (6%) por baja Defensor (→ Beneficia Toluca): Willer Ditta
  λ_final = 2.0023
  Impacto Total: +4.6%

Cruz Azul (Visita):
  λ_base  = 1.4440
  [AWAY] [-5.0%] Reducción Lambda Propio (5%) por baja Mediocampista: Andrés Montaño
  λ_final = 1.3718
  Impacto Total: -5.0%
```

**Probabilidades Generales:** Local 50.9% | Empate 24.1% | Visita 25.0%

### 🎯 Mejores Opciones (Ranking por Valor Esperado)
| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |
| :--- | :--- | :--- | :--- | :--- |
| **2-1** | HOME | 9.4% | 50.9% | **0.603** |
| 2-0 | HOME | 6.9% | 50.9% | 0.578 |
| 3-1 | HOME | 6.3% | 50.9% | 0.572 |
| 1-0 | HOME | 5.6% | 50.9% | 0.566 |
| 1-1 | DRAW | 10.6% | 24.1% | 0.347 |
| 1-2 | AWAY | 6.5% | 25.0% | 0.314 |
| 2-2 | DRAW | 6.5% | 24.1% | 0.305 |
| 0-0 | DRAW | 4.7% | 24.1% | 0.287 |

## Atlas vs. Pumas
### 🗞️ Contexto y Novedades
- 🔥 **PRESSURE:** Diego Cocca llegó en agosto 2025 tras mal Apertura (lugar 14). Sin buenas esperanzas en torno a los Zorros
- ℹ️ **FORM:** Pumas tercero en la tabla, duelo inesperado en las alturas. Efraín Juárez en buen momento *(info, no ajusta modelo)*

**Movimientos de Mercado:**
- 🔴 **BAJA (Atlas):** Matías Cóccaro (delantero)
- 🔴 **BAJA (Atlas):** Mauro Manotas (delantero)
- 🟢 **ALTA (Pumas):** Uriel Antuna (extremo)
- 🟢 **ALTA (Pumas):** Jordan Carrillo (mediocampista)

**Ausencias Relevantes:**
- ⚠️ Duda **(Atlas):** Diego González - *lesión por distensión (17 enero)*
- ⚠️ Duda **(Atlas):** Jorge Rodríguez ⭐ Top-40 (Rating: 7.27) - *lesión por golpe (31 enero)*
- 🚑 Baja **(Pumas):** Santiago Trigos - *lesión*
- 🚑 Baja **(Pumas):** Adriano Leone - *lesión*
- 🚑 Baja **(Pumas):** José Macías - *lesión*
- 🚑 Baja **(Pumas):** Lisandro Magallán - *suspensión*

### 🧪 Análisis de Lambdas (Goles Esperados)
**Atlas (Local) = 1.6100**
- *Fuerza Ataque*: 0.935 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.953
- *Media Liga Local*: 1.81
- *Cálculo Base*: 0.935 * 0.953 * 1.81 = 1.614

**Pumas (Visita) = 1.4656**
- *Fuerza Ataque*: 1.095 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 1.188
- *Media Liga Visita*: 1.29
- *Cálculo Base*: 1.095 * 1.188 * 1.29 = 1.678

**📊 Desglose Completo de Ajustes:**
```
Atlas (Local):
  λ_base  = 1.6135
  [HOME] [-4.5%] Reducción Lambda Propio (9%) por baja Atacante (Duda: 50% efecto): Diego González
  [HOME] [-2.5%] Reducción Lambda Propio (5%) por baja Mediocampista (Duda: 50% efecto): Jorge Rodríguez
  [HOME] [-1.3%] Reducción Lambda Propio (9%) por BAJA/Transferencia Atacante (Pond. Hist: 15%): Matías Cóccaro
  [HOME] [-1.3%] Reducción Lambda Propio (9%) por BAJA/Transferencia Atacante (Pond. Hist: 15%): Mauro Manotas
  [HOME] [+6.0%] Aumento Lambda Rival (6%) por baja Defensor (→ Beneficia Atlas): Adriano Leone
  [HOME] [+6.0%] Aumento Lambda Rival (6%) por baja Defensor (→ Beneficia Atlas): Lisandro Magallán
  [HOME] [-2.0%] Ligera Penalización por Presión/Entorno: Diego Cocca llegó en agosto 2025 tras mal Apertura (lugar 14). Sin buenas esperanzas en torno a los Zorros
  λ_final = 1.6100
  Impacto Total: -0.2%

Pumas (Visita):
  λ_base  = 1.6776
  [AWAY] [-5.0%] Reducción Lambda Propio (5%) por baja Mediocampista: Santiago Trigos
  [AWAY] [-9.0%] Reducción Lambda Propio (9%) por baja Atacante: José Macías
  [AWAY] [+0.8%] BOOST Lambda Propio (5%) por Fichaje Goleador Top (Pond. Hist: 15%, Adapt: 100%): Uriel Antuna
  [AWAY] [+0.3%] BOOST Lambda Propio (2%) por Fichaje Medio (Pond. Hist: 15%, Adapt: 100%): Jordan Carrillo
  λ_final = 1.4656
  Impacto Total: -12.6%
```

**🔍 Interpretación:**
- Los ajustes DISMINUYÓ significativamente (-12.6%) los goles esperados de Pumas
- Esto modifica las probabilidades de resultado y marcador final

**Probabilidades Generales:** Local 39.8% | Empate 26.7% | Visita 33.5%

### 🎯 Mejores Opciones (Ranking por Valor Esperado)
| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |
| :--- | :--- | :--- | :--- | :--- |
| **2-1** | HOME | 8.8% | 39.8% | **0.485** |
| 1-0 | HOME | 6.0% | 39.8% | 0.458 |
| 2-0 | HOME | 6.0% | 39.8% | 0.458 |
| 1-2 | AWAY | 8.0% | 33.5% | 0.415 |
| 1-1 | DRAW | 12.3% | 26.7% | 0.390 |
| 0-1 | AWAY | 5.3% | 33.5% | 0.389 |
| 2-2 | DRAW | 6.4% | 26.7% | 0.332 |
| 0-0 | DRAW | 6.0% | 26.7% | 0.328 |

## Pachuca vs. FC Juarez
### 🗞️ Contexto y Novedades
- ℹ️ **FORM:** Pachuca fue creciendo después de perder en su presentación, busca vencer a Juárez por primera vez en cuatro enfrentamientos *(info, no ajusta modelo)*
- ℹ️ **FORM:** FC Juárez solo ha sumado un punto en el torneo *(info, no ajusta modelo)*

**Ausencias Relevantes:**
- 🚑 Baja **(Pachuca):** Carlos Moreno - *suspensión*
- 🚑 Baja **(Pachuca):** Andrés Micolta - *fractura de rótula derecha, operado, 4-5 meses fuera (puede perderse todo el torneo)*
- 🚑 Baja **(Pachuca):** Elías Montiel - *lesión de isquiotibiales, regreso finales de febrero*
- ⚠️ Duda **(Pachuca):** Alan Mozo - *lesión por golpe*

### 🧪 Análisis de Lambdas (Goles Esperados)
**Pachuca (Local) = 1.0661**
- *Fuerza Ataque*: 0.632 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.981
- *Media Liga Local*: 1.81
- *Cálculo Base*: 0.632 * 0.981 * 1.81 = 1.122

**FC Juarez (Visita) = 1.1531**
- *Fuerza Ataque*: 1.032 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.778
- *Media Liga Visita*: 1.29
- *Cálculo Base*: 1.032 * 0.778 * 1.29 = 1.037

**📊 Desglose Completo de Ajustes:**
```
Pachuca (Local):
  λ_base  = 1.1222
  [HOME] [-5.0%] Reducción Lambda Propio (5%) por baja Mediocampista: Elías Montiel
  λ_final = 1.0661
  Impacto Total: -5.0%

FC Juarez (Visita):
  λ_base  = 1.0366
  [AWAY] [+8.0%] Aumento Lambda Rival (8%) por baja Portero Rotación (→ Beneficia FC Juarez): Carlos Moreno
  [AWAY] [+3.0%] Aumento Lambda Rival (6%) por baja Defensor (Duda: 50% efecto) (→ Beneficia FC Juarez): Alan Mozo
  λ_final = 1.1531
  Impacto Total: +11.2%
```

**🔍 Interpretación:**
- Los ajustes AUMENTÓ significativamente (+11.2%) los goles esperados de FC Juarez
- Esto modifica las probabilidades de resultado y marcador final

**Probabilidades Generales:** Local 31.6% | Empate 32.4% | Visita 36.0%

### 🎯 Mejores Opciones (Ranking por Valor Esperado)
| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |
| :--- | :--- | :--- | :--- | :--- |
| **1-1** | DRAW | 15.1% | 32.4% | **0.475** |
| 0-1 | AWAY | 10.8% | 36.0% | 0.468 |
| 0-0 | DRAW | 12.6% | 32.4% | 0.450 |
| 1-2 | AWAY | 7.7% | 36.0% | 0.437 |
| 0-2 | AWAY | 7.2% | 36.0% | 0.432 |
| 1-0 | HOME | 9.8% | 31.6% | 0.415 |
| 2-1 | HOME | 7.1% | 31.6% | 0.387 |
| 2-0 | HOME | 6.2% | 31.6% | 0.378 |

## CF America vs. Monterrey
### 🗞️ Contexto y Novedades
- ℹ️ **REESTRUCTURACION:** América vivió semana caótica: salidas de Fidalgo (a Betis) y Saint-Maximin (a RC Lens, tras incidentes racismo). Llegada de emergencia de Raphael Veiga desde Palmeiras. Noveno lugar con 5 puntos *(info, no ajusta modelo)*
- ✈️ **CONCACAF_LOAD:** Monterrey con carga de Concachampions: jugó vs Xelajú el miércoles 4 feb, juega vs América el sábado 7, y vuelta vs Xelajú el miércoles 11 feb
- ℹ️ **RIVALRY:** América busca revancha: Monterrey los eliminó de la Liguilla pasada en el Estadio Ciudad de los Deportes *(info, no ajusta modelo)*

**Movimientos de Mercado:**
- 🔴 **BAJA (CF America):** Álvaro Fidalgo (mediocampista)
- 🔴 **BAJA (CF America):** Allan Saint-Maximin (extremo)
- 🟢 **ALTA (CF America):** Raphael Veiga (mediocampista ofensivo)

**Ausencias Relevantes:**
- 🚑 Baja **(CF America):** Alejandro Zendejas - *lesión, baja sensible en banda derecha*
- 🚑 Baja **(CF America):** Israel Reyes ⭐ Top-40 (Rating: 7.43) - *lesión*

### 🧪 Análisis de Lambdas (Goles Esperados)
**CF America (Local) = 1.9176**
- *Fuerza Ataque*: 1.127 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 1.104
- *Media Liga Local*: 1.81
- *Cálculo Base*: 1.127 * 1.104 * 1.81 = 2.253

**Monterrey (Visita) = 1.0994**
- *Fuerza Ataque*: 1.455 (Pond: 0.85 Actual + 0.15 Prior)
- *Fuerza Defensa Rival*: 0.582
- *Media Liga Visita*: 1.29
- *Cálculo Base*: 1.455 * 0.582 * 1.29 = 1.092

**📊 Desglose Completo de Ajustes:**
```
CF America (Local):
  λ_base  = 2.2528
  [HOME] [-12.0%] Reducción Lambda Propio (12%) por baja Goleador Top: Alejandro Zendejas
  [HOME] [-1.5%] Reducción Lambda Propio (10%) por BAJA/Transferencia Creativo Top (Pond. Hist: 15%): Álvaro Fidalgo
  [HOME] [-1.8%] Reducción Lambda Propio (12%) por BAJA/Transferencia Goleador Top (Pond. Hist: 15%): Allan Saint-Maximin
  λ_final = 1.9176
  Impacto Total: -14.9%

Monterrey (Visita):
  λ_base  = 1.0918
  [AWAY] [+6.0%] Aumento Lambda Rival (6%) por baja Defensor (→ Beneficia Monterrey): Israel Reyes
  [AWAY] [-5.0%] Reducción por Fatiga/Rotación (Concacaf): Monterrey con carga de Concachampions: jugó vs Xelajú el miércoles 4 feb, juega vs América el sábado 7, y vuelta vs Xelajú el miércoles 11 feb
  λ_final = 1.0994
  Impacto Total: +0.7%
```

**🔍 Interpretación:**
- Los ajustes DISMINUYÓ significativamente (-14.9%) los goles esperados de CF America
- Esto modifica las probabilidades de resultado y marcador final

**Probabilidades Generales:** Local 55.1% | Empate 24.8% | Visita 20.1%

### 🎯 Mejores Opciones (Ranking por Valor Esperado)
| Marcador | Tipo | P.Exacta | P.Gral | **Valor Esperado** |
| :--- | :--- | :--- | :--- | :--- |
| **2-1** | HOME | 9.9% | 55.1% | **0.650** |
| 2-0 | HOME | 9.0% | 55.1% | 0.641 |
| 1-0 | HOME | 8.0% | 55.1% | 0.631 |
| 3-1 | HOME | 6.3% | 55.1% | 0.614 |
| 3-0 | HOME | 5.8% | 55.1% | 0.608 |
| 1-1 | DRAW | 11.7% | 24.8% | 0.364 |
| 0-0 | DRAW | 6.2% | 24.8% | 0.310 |
| 1-2 | AWAY | 5.7% | 20.1% | 0.258 |

# 🏆 Resumen Final: Picks Recomendados

| Partido | Pick Óptimo | Valor (Puntos Esp.) | Tendencia Base |
| :--- | :---: | :---: | :---: |
| Tigres vs Santos Laguna | **2-0** | EV: 1.009 | HOME (81%) |
| Necaxa vs Atletico de San Luis | **0-1** | EV: 0.635 | AWAY (47%) |
| Tijuana vs Puebla | **2-0** | EV: 1.028 | HOME (84%) |
| Mazatlán vs CD Guadalajara | **1-2** | EV: 0.729 | AWAY (63%) |
| Queretaro FC vs León | **1-0** | EV: 0.825 | HOME (60%) |
| Toluca vs Cruz Azul | **2-1** | EV: 0.603 | HOME (51%) |
| Atlas vs Pumas | **2-1** | EV: 0.485 | HOME (40%) |
| Pachuca vs FC Juarez | **1-1** | EV: 0.475 | DRAW (32%) |
| CF America vs Monterrey | **2-1** | EV: 0.650 | HOME (55%) |

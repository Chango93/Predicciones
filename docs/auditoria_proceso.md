# Auditoría del proceso de predicciones

## Alcance
Esta auditoría revisa el flujo canónico (`run_pipeline.py`), la lógica de cálculo en `src/predicciones`, y los archivos efectivamente consumidos por los scripts de generación.

## Workflow real (intención del proyecto)
1. `run_pipeline.py` valida imports y ejecuta 3 pasos en secuencia:
   - `gen_predicciones.py`
   - `gen_reporte_tecnico.py`
   - `diagnostico_lambda.py`
2. Los tres scripts consumen el núcleo compartido en `src/predicciones/core.py`.
3. Todos usan `src/predicciones/config.py` (configuración global `CONFIG`, actualmente fija en jornada 6).
4. Los ajustes cualitativos y bajas se consolidan vía `src/predicciones/data.py`.

## Lógica funcional por módulo
- **Core (`src/predicciones/core.py`)**
  - Normalización/canonicalización de equipos.
  - Construcción de stats por torneo.
  - Priors multi-torneo con pesos y caché (`data/processed/prior_cache_<hash>.json`).
  - Cálculo central de lambdas: suavizado de medias de liga, EB por tasas, blending dinámico, clamps y ajustes por contexto.

- **Predicciones (`gen_predicciones.py`)**
  - Carga partidos, stats y ajustes (bajas + investigación cualitativa).
  - Calcula lambdas por partido con `compute_components_and_lambdas`.
  - Simula grilla Poisson 0–5 para obtener probabilidades 1X2, marcador exacto y EV.
  - Exporta `predicciones_jornada_<N>_final.csv`.

- **Reporte (`gen_reporte_tecnico.py`)**
  - Reutiliza la misma lógica del core para reproducibilidad del análisis.
  - Genera Markdown técnico con picks, desgloses de ajustes y ranking EV.
  - Exporta `reporte_tecnico_jornada_<N>.md`.

- **Diagnóstico (`diagnostico_lambda.py`)**
  - Ejecuta validaciones fail-fast (duplicados, sanidad de lambdas, cobertura, etc.).
  - Exporta `diagnostico_lambda_components.csv` y `diagnostico_report.txt`.

## Archivos que **sí** utiliza el proceso (ruta actual)
### Inputs principales (desde `config.CONFIG`)
- `jornada_6_final.json` (partidos)
- `Stats_liga_mx.json` (histórico para stats/prior)
- `evaluacion_bajas.json` (bajas estructuradas)
- `Investigacion_cualitativa_jornada6.json` (contexto cualitativo)

### Código realmente involucrado
- `run_pipeline.py`
- `gen_predicciones.py`
- `gen_reporte_tecnico.py`
- `diagnostico_lambda.py`
- `src/predicciones/config.py`
- `src/predicciones/core.py`
- `src/predicciones/data.py`
- `src/predicciones/utils.py`

### Outputs esperados
- `predicciones_jornada_6_final.csv`
- `reporte_tecnico_jornada_6.md`
- `diagnostico_lambda_components.csv`
- `diagnostico_report.txt`
- `fingerprint_jornada_6.json` (si el pipeline llega al final)

## Incongruencias detectadas
1. **`run_pipeline.py` no puede completar su propio final**:
   - Usa `json.dump(...)` pero no importa `json`.
   - Usa `timestamp_start` al final, pero nunca se define.

2. **Guardia legacy parcial**:
   - `check_legacy_guard()` revisa `diagnostico_visitante.py` y `modelo.py` en raíz.
   - Existe lógica legacy dentro de `/legacy`, por lo que la guardia no previene todas las rutas de ejecución fuera del flujo canónico.

3. **Dependencia de entorno no resuelta**:
   - El pipeline falla de entrada si no está instalado `pandas`.
   - Actualmente no hay validación de dependencias previa ni archivo de requirements en este chequeo.

4. **Config fija a jornada 6**:
   - Existe `get_config(jornada)`, pero el flujo productivo usa `CONFIG = get_config(6)` por default.
   - Sin sobreescritura explícita, todo el proceso opera jornada 6 aunque existan otros JSON de jornada.

5. **Ruido de mantenimiento en scripts**:
   - Comentarios intermedios en `run_pipeline.py` reflejan dudas sobre outputs (`OUTPUT_CSV` vs entregables principales), lo cual sugiere deuda técnica documental.

## Riesgo/impacto
- Riesgo alto de falsa sensación de “pipeline canónico operativo” cuando en realidad no finaliza en un entorno sin dependencias completas.
- Riesgo medio de ejecución inconsistente por mezcla de scripts activos y legacy.
- Riesgo medio de errores operativos al cambiar de jornada por configuración hardcodeada.

## Recomendación de workflow objetivo
1. Parametrizar jornada desde CLI/ENV y generar `CONFIG` dinámico.
2. Agregar preflight de dependencias (pandas/scipy) antes de ejecutar pasos.
3. Corregir `run_pipeline.py` (`import json`, `timestamp_start`).
4. Definir manifest de entradas/salidas por jornada y validarlo en preflight.
5. Mantener `legacy/` fuera de cualquier path ejecutable y documentar oficialmente el flujo en README.


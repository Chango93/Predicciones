import os
import json
import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_command(command):
    print(f"[RUN] Ejecutando: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"[ERROR] Al ejecutar: {command}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Automatización de Predicciones Liga MX")
    parser.add_argument("--jornada", type=int, default=5, help="Número de la jornada a procesar")
    parser.add_argument("--season", type=str, default="2025-2026", help="Temporada (ej: 2025-2026)")
    parser.add_argument("--skip-fetch", action="store_true", help="Saltar la descarga de datos de la API")
    args = parser.parse_args()

    jornada_num = args.jornada
    season = args.season
    
    print(f"\n*** INICIANDO PIPELINE DE PREDICCION - JORNADA {jornada_num} ***")
    print("====================================================")

    # Paths usando nueva estructura
    file_user_notes = f"data/raw/jornada {jornada_num}.json"
    file_api_data = f"data/processed/jornada_{jornada_num}_api.json"
    file_merged = f"data/processed/jornada_{jornada_num}_final.json"

    # 1. Verificar archivo de notas del usuario
    if not os.path.exists(file_user_notes):
        print(f"[WARNING] ADVERTENCIA: No se encontró '{file_user_notes}'.")
        print("   El modelo correrá solo con datos de API (sin tus notas de bajas/contexto).")
        input("   Presiona ENTER para continuar o Ctrl+C para cancelar...")
    else:
        print(f"[OK] Archivo de notas detectado: {file_user_notes}")

    # 2. Obtener datos frescos de la API (src/fetcher.py)
    if not args.skip_fetch:
        print("\n[Paso 1/3] Descargando datos cuantitativos de la API...")
        cmd_fetch = f'python src/fetcher.py --season {season} --jornada {jornada_num}'
        if not run_command(cmd_fetch):
            print("[ERROR] Falló la descarga de datos. Verifica tu conexión o el script.")
            if not os.path.exists(file_api_data):
                sys.exit(1)
    
    # 3. Fusionar datos (src/merger.py)
    print(f"\n[Paso 2/3] Fusionando datos API + Notas Usuario + Parches Históricos...")
    
    if jornada_num == 5:
        if not run_command("python src/merger.py"):
             sys.exit(1)
    else:
        print("[WARNING] AVISO: El script automático de fusión 'src/merger.py' está optimizado para la Jornada 5.")
        print("   Para otras jornadas, asegúrate que 'src/fetcher.py' traiga los stats históricos correctos.")
        # Fallback: copy API to Final directly if no merge script available
        import shutil
        if os.path.exists(file_api_data):
            shutil.copy(file_api_data, file_merged)
            print(f"   (Copia directa de {file_api_data} a {file_merged})")

    # 4. Ejecutar Modelo (src/modelo.py)
    print(f"\n[Paso 3/3] Corriendo Modelo de Predicción (Determinista)...")
    if os.path.exists(file_merged):
        cmd_model = f'python src/modelo.py --input "{file_merged}"'
        run_command(cmd_model)
    else:
        print(f"[ERROR] Crítico: No se generó el archivo final '{file_merged}'.")
        sys.exit(1)

    print("\n====================================================")
    print("[OK] PROCESO COMPLETADO")
    print(f"[FILE] Reporte generado: reports/reporte_tecnico_automatico.md")
    print("====================================================")

if __name__ == "__main__":
    main()

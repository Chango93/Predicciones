
"""
PIPELINE CANON DE PREDICCIONES
Ejecuta la secuencia completa de generación de predicciones y reportes.
Fuente de Verdad: src.predicciones.core
"""

import os
import sys
import subprocess
import hashlib
import importlib.util
from datetime import datetime

# Importar configuración para conocer inputs/outputs
try:
    import src.predicciones.config as config
    import src.predicciones.utils as utils  # Importar utils para git info
except ImportError:
    print("FATAL: No se puede importar src.predicciones.config o src.predicciones.utils")
    sys.exit(1)

def calculate_file_hash(filepath):
    """Calcula SHA256 de un archivo."""
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_legacy_guard():
    """Detecta archivos legacy peligrosos."""
    legacy_files = ["diagnostico_visitante.py", "modelo.py"]
    found = []
    for f in legacy_files:
        if os.path.exists(f):
            found.append(f)
    
    if found:
        print("\n" + "!" * 80)
        print("WARNING: LEGACY SCRIPT DETECTED")
        for f in found:
            print(f"  - {f}")
        print("DO NOT USE THESE FILES. THEY CONTAIN OUTDATED LOGIC.")
        print("SUGGESTION: Move them to a 'legacy/' execution folder or delete them.")
        print("!" * 80 + "\n")
        return False
    return True

def validate_runtime_imports():
    """Valida que el core sea el correcto."""
    print("-" * 80)
    print("VALIDACION DE RUNTIME")
    
    try:
        import src.predicciones.core as core
        print(f"CORE IMPORTADO: {core.__file__}")
        
        # Check signature verification (simple existence check)
        if hasattr(core, 'compute_components_and_lambdas'):
            print("  [OK] compute_components_and_lambdas existe en core")
        else:
            print("  [ERROR] compute_components_and_lambdas NO encontrado en core")
            
    except ImportError as e:
        print(f"  [ERROR] No se pudo importar src.predicciones.core: {e}")
        return False
        
    print("-" * 80)
    return True

def run_step(script_name, description):
    """Ejecuta un script de python como subprocess."""
    print(f"\n>>> EJECUTANDO: {description} ({script_name})...")
    start_time = datetime.now()
    
    # Force stdout to utf-8 just in case
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    try:
        result = subprocess.run(
            ["python", script_name],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8' # Force usage of UTF-8 for child output
        )
        print(f"  [OK] Completado en {datetime.now() - start_time}")
        # Print first few lines of output
        lines = result.stdout.splitlines()
        for line in lines[:3]:
            try:
                print(f"  > {line}")
            except UnicodeEncodeError:
                print(f"  > [Non-printable content]")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Falló ejecución de {script_name}")
        # Handle potential encoding issues when printing error output
        try:
            print("  STDOUT:", e.stdout)
        except:
            print("  STDOUT: (Unprintable)")
        try:
            print("  STDERR:", e.stderr)
        except:
            print("  STDERR: (Unprintable)")
        return False

def main():
    print("=" * 80)
    print(f"INICIANDO PIPELINE CANON - {datetime.now()}")
    print("=" * 80)
    
    # 1. Anti-Legacy Guard
    check_legacy_guard()
    
    # 2. Runtime Validation
    if not validate_runtime_imports():
        sys.exit(1)
        
    # 3. Execution Sequence
    steps = [
        ("gen_predicciones.py", "Generación de CSV de Predicciones"),
        ("gen_reporte_tecnico.py", "Generación de Reporte Markdown"),
        ("diagnostico_lambda.py", "Auditoría de Sistema (Diagnóstico)")
    ]
    
    for script, desc in steps:
        if not run_step(script, desc):
            print("\nPipeline ABORTADO por error.")
            sys.exit(1)
            
    # 4. Summary & Hashes
    print("\n" + "=" * 80)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 80)
    
    jornada = config.CONFIG.get('JORNADA', 'X')
    
    csv_file = config.CONFIG['OUTPUT_CSV'] # Usually diagnostico_lambda_components.csv? 
    # Wait, gen_predicciones produces 'predicciones_jornada_6_final.csv'
    # And gen_reporte produces 'reporte_tecnico_jornada_6.md'
    # config.OUTPUT_CSV is 'diagnostico_lambda_components.csv' (diag output)
    
    # Let's target the MAIN deliverables
    files_to_hash = [
        f"predicciones_jornada_{jornada}_final.csv",
        f"reporte_tecnico_jornada_{jornada}.md",
        config.CONFIG['OUTPUT_CSV']
    ]
    
    # === GENERAR FINGERPRINT DE EJECUCION ===
    jornada = config.CONFIG['JORNADA']
    fingerprint = {
        'timestamp': datetime.now().isoformat(),
        'config_version': '2026.02.11',
        'jornada': jornada,
        'git_commit': utils.get_git_commit(),
        'git_dirty': utils.is_git_dirty(),
        'input_hashes': {
            'stats': calculate_file_hash(config.CONFIG['INPUT_STATS']),
            'matches': calculate_file_hash(config.CONFIG['INPUT_MATCHES']),
            'bajas': calculate_file_hash(config.CONFIG['INPUT_EVALUATION']),
            'qualitative': calculate_file_hash(config.CONFIG['INPUT_QUALITATIVE']),
        },
        'config_hash': utils.calculate_config_hash(config.CONFIG),
        'output_hashes': {}
    }

    # === CALCULAR HASHES DE SALIDA ===
    print("-" * 80)
    print("CALCULO DE HASHES SHA-256 (Determinismo)")
    
    files_to_hash = [
        f"predicciones_jornada_{jornada}_final.csv",
        f"reporte_tecnico_jornada_{jornada}.md",
        config.CONFIG['OUTPUT_TXT'] # Diagnostico report
    ]
    
    for f in files_to_hash:
        h = calculate_file_hash(f)
        fingerprint['output_hashes'][f] = h
        print(f"  {f:<35} : {h}")
        
    # Guardar fingerprint
    fp_filename = f"fingerprint_jornada_{jornada}.json"
    with open(fp_filename, 'w') as f:
        json.dump(fingerprint, f, indent=2)
    print(f"\n[OK] Fingerprint guardado: {fp_filename}")
        
    print("-" * 80)
    print(f"PIPELINE FINALIZADO EN {datetime.now() - timestamp_start}")
    print("=" * 80)
    print("PIPELINE COMPLETADO EXITOSAMENTE")

if __name__ == "__main__":
    main()

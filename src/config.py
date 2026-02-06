"""
Configuración centralizada del proyecto de predicciones Liga MX
"""

# === API Configuration ===
API_KEY = "180725"
LEAGUE_ID = "4350"  # Liga MX
BASE_URL = "https://www.thesportsdb.com/api/v1/json"
DEFAULT_SEASON = "2025-2026"

# === Cache Configuration ===
CACHE_FILE = "data/cache/event_stats_cache.json"

# === DOM Score Configuration ===
DOM_MIN_MATCHES = 3  # Minimum matches with detailed stats to use DOM
DOM_MAX_AGE_DAYS = 60  # Only use stats from matches in last N days

# === Model Parameters ===
# League averages
LEAGUE_AVG_HOME_G = 1.81
LEAGUE_AVG_AWAY_G = 1.29
LEAGUE_AVG_GLOBAL = (LEAGUE_AVG_HOME_G + LEAGUE_AVG_AWAY_G) / 2
LEAGUE_DOM_AVG = 4.0  # Baseline DOM score

# Model coefficients
K_DOM = 0.04  # DOM impact factor
DEFAULT_RHO = -0.13  # Dixon-Coles correlation parameter

# Simulation settings
SIMULATIONS = 20000  # Monte Carlo simulations (deprecated with deterministic EV)

# === Roster Adjustment Configuration ===
# Valid evidence sources
VALID_EVIDENCE_SOURCES = [
    "oficial_club",
    "liga_mx_oficial", 
    "medio_top",
    "stats_db_top",
    "alto_confirmado",
    "medio_declaraciones"
]

# === File Paths ===
DATA_RAW_DIR = "data/raw"
DATA_PROCESSED_DIR = "data/processed"
DATA_CACHE_DIR = "data/cache"
REPORTS_DIR = "reports"

# === Logging Configuration ===
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "logs/predicciones.log"

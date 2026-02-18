import pandas as pd
import numpy as np
import src.predicciones.config as config
import src.predicciones.core as dl

def calculate_recent_form(stats_df, team_name, match_date, n=5):
    """
    Calculates a form multiplier based on the last N games.
    """
    # Ensure date column is datetime
    if not np.issubdtype(stats_df['date'].dtype, np.datetime64):
        stats_df['date'] = pd.to_datetime(stats_df['date'], dayfirst=True)
        
    match_date = pd.to_datetime(match_date)
    
    # Filter for team matches before the specific date
    # We need to check both home_team and away_team columns
    # And we need to use canonical names for comparison if possible, 
    # but stats_df might have raw names. 
    # Ideally stats_df should have been pre-processed, but we can do a quick apply here 
    # or just assume the caller handles it. 
    # Given the pipeline structure, stats_df is raw from CSV.
    
    # Efficiency: create a mask. 
    # We will normalize the team name we are looking for.
    # And we will normalize the dataframe columns on the fly or assuming they are somewhat cleaner.
    # 'Stats_liga_mx.json' usually has specific names.
    
    # Let's try to filter using the string containment or exact match if we know the mapping.
    # better to use dl.canonical_team_name on the df if it's small enough, or just iterate.
    # Stats file is small (~600 rows).
    
    # Create a copy to avoid SettingWithCopy warning on the main df if we modify it
    df = stats_df.copy()
    
    # Normalize team names in df for accurate matching
    # unique_teams = pd.concat([df['home_team'], df['away_team']]).unique()
    # mapping = {t: dl.canonical_team_name(t) for t in unique_teams}
    # df['home_canon'] = df['home_team'].map(mapping)
    # df['away_canon'] = df['away_team'].map(mapping)
    
    # Fast filtering
    # We assume 'team_name' passed in is already canonical.
    
    # To avoid mapping everything, apply canonicalization in lambda (slower but safe)
    # or just rely on the fact that we can search for the name.
    
    # Let's do it robustly.
    # df['home_canon'] = df['home_team'].apply(dl.canonical_team_name) # OPTIMIZACION: Ya viene de afuera
    # df['away_canon'] = df['away_team'].apply(dl.canonical_team_name) # OPTIMIZACION: Ya viene de afuera
    
    if 'home_canon' not in df.columns:
         df['home_canon'] = df['home_team'].apply(dl.canonical_team_name)
    if 'away_canon' not in df.columns:
         df['away_canon'] = df['away_team'].apply(dl.canonical_team_name)
    
    team_matches = df[
        ((df['home_canon'] == team_name) | (df['away_canon'] == team_name)) & 
        (df['date'] < match_date)
    ].sort_values('date', ascending=False).head(n)
    
    if len(team_matches) < 3:
        return 1.0, {"status": "insufficient_data", "games": len(team_matches), "pct": 0.5} # Neutral 0.5 pct
        
    points = 0
    max_points = len(team_matches) * 3
    
    for _, row in team_matches.iterrows():
        is_home = (row['home_canon'] == team_name)
        gf = row['home_goals'] if is_home else row['away_goals']
        ga = row['away_goals'] if is_home else row['home_goals']
        
        if gf > ga:
            points += 3
        elif gf == ga:
            points += 1
            
    pct_points = points / max_points if max_points > 0 else 0
    
    # Config values
    # RECENT_FORM_MAX_WEIGHT defaults to 0.05
    boost_max = 0.05
    penalty_max = 0.05
    
    multiplier = 1.0
    
    if pct_points >= 0.60:
        # Scale from 0.60 (1.0) to 1.00 (1.05)
        factor = (pct_points - 0.60) / 0.40
        multiplier = 1.0 + (factor * boost_max)
        
    elif pct_points <= 0.30:
        # Scale from 0.0 (0.95) to 0.30 (1.0)
        factor = (0.30 - pct_points) / 0.30
        multiplier = 1.0 - (factor * penalty_max)
        
    return multiplier, {
        "status": "calculated",
        "games": len(team_matches),
        "points": points,
        "max_points": max_points,
        "pct": pct_points,
        "multiplier": multiplier
    }

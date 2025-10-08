to run this model there's a few steps.

first; train the model on the data range from 2006-2025, set the week in 
"def run_r_aggregation(prop_name, seasons=range(2006, 2026), max_week_2025=3):"

second; run predict_upcoming.py to run predictions on matchups for the upcoming week.
input the data that is prompted when running the file, to feed the model data needed to 
run the predictions.

third; after the games are over, run update_actuals.R to update the result of the passing yards for the qb's that week. 

running each file in the command line like this:

python -m src.train_pipeline

python -m src.predict_upcoming

Rscript update_actuals.R 'x' - where 'x' is the week or the sheet number to update.

============================================================
MODEL PERFORMANCE DIAGNOSTICS
============================================================

OVERALL RECORD: 51-54 (48.6%)
Total predictions: 108

PREDICTION ACCURACY:
  Mean Absolute Error (MAE): 59.3 yards
  Median Absolute Error: 53.7 yards
  Mean % Error: 34.9%
  Std Dev of Errors: 75.2 yards

OVER BETS: 52 total
  Record: 22-30 (42.3%)
  Avg prediction error: 26.1 yards

UNDER BETS: 53 total
  Record: 29-24 (54.7%)
  Avg prediction error: -16.8 yards

HOME GAMES: 52 total
  Record: 26-26 (50.0%)

AWAY GAMES: 53 total
  Record: 25-28 (47.2%)

CLOSE TO LINE (≤10 yards difference):
  Total: 38
  Record: 15-23 (39.5%)
  → Maybe avoid betting close lines

FAR FROM LINE (>10 yards difference):
  Total: 67
  Record: 36-31 (53.7%)

WORST PREDICTIONS (biggest errors):
    Player Team  Mean Pred  Actual  abs_error  Lean WL
  R.Wilson  NYG 207.800003   450.0 242.199997 UNDER  L
  J.Fields  NYJ 208.000000    27.0 181.000000  OVER  L
  J.Burrow  CIN 282.600006   113.0 169.600006  OVER  L
   J.Allen  BUF 234.699997   394.0 159.300003 UNDER  L
D.Prescott  DAL 209.300003   361.0 151.699997 UNDER  L

BEST PREDICTIONS (smallest errors):
   Player Team  Mean Pred  Actual  abs_error  Lean WL
S.Darnold  SEA 218.199997   218.0   0.199997 UNDER  L
   D.Maye   NE 203.899994   203.0   0.899994 UNDER  W
P.Mahomes   KC 259.000000   258.0   1.000000 UNDER  L
S.Rattler   NO 216.500000   218.0   1.500000  OVER  W
S.Rattler   NO 208.899994   207.0   1.899994 UNDER  W

============================================================
RECOMMENDATIONS:
============================================================
3. Avoid close lines (≤10 yards): only 39.5% win rate

4. Next steps to improve:
   - Add more features (weather, injuries, opponent strength)
   - Tune the probability threshold (currently using mean prediction)
   - Consider recent form more heavily
   - Add situational adjustments (division games, primetime, etc.)



============================================================================================
============================================================================================

   # Batch Import Template for QB Passing Yards Predictions

## CSV File Format

Create a CSV file with the following columns (header row required):

```csv
player_name,posteam,defteam,line,is_home
P.Mahomes,KC,ATL,265.5,1
J.Allen,BUF,MIA,242.5,0
J.Hurts,PHI,DAL,225.5,1
L.Jackson,BAL,CIN,248.5,0
```

## Column Descriptions

| Column | Description | Example | Required |
|--------|-------------|---------|----------|
| `player_name` | Player name (must match historical data format) | `P.Mahomes` | Yes |
| `posteam` | Player's team (3-letter code) | `KC` | Yes |
| `defteam` | Opponent defense (3-letter code) | `ATL` | Yes |
| `line` | Vegas line (decimal) | `265.5` | Yes |
| `is_home` | Home game? (1=yes, 0=no) | `1` | Yes |

## Valid Team Codes

ARI, ATL, BAL, BUF, CAR, CHI, CIN, CLE, DAL, DEN, DET, GB, HOU, IND, JAX, KC, LA, LAC, LV, MIA, MIN, NE, NO, NYG, NYJ, PHI, PIT, SEA, SF, TB, TEN, WAS

## Example Files

### Week 4 Example (`data/week4_batch.csv`)
```csv
player_name,posteam,defteam,line,is_home
P.Mahomes,KC,LAC,275.5,1
J.Allen,BUF,BAL,255.5,0
J.Hurts,PHI,TB,230.5,1
L.Jackson,BAL,BUF,248.5,1
D.Prescott,DAL,NYG,265.5,0
```

### Week 5 Example (`data/week5_batch.csv`)
```csv
player_name,posteam,defteam,line,is_home
J.Burrow,CIN,ARI,285.5,1
T.Tagovailoa,MIA,NE,252.5,0
C.Williams,CHI,CAR,220.5,1
A.Richardson,IND,JAX,215.5,0
```

## Usage

1. Create your CSV file with the required columns
2. Run `python predict_upcoming.py`
3. Enter the week number
4. Choose option 1 (Batch import)
5. Enter the path to your CSV file (e.g., `data/week4_batch.csv`)

The script will:
- Validate all team codes and player names
- Skip any players already predicted for that week
- Generate predictions for all valid entries
- Save results to the Excel file

## Tips

- Save CSV files in the `data/` folder for easy access
- Use consistent player name format (check existing data for exact spelling)
- Double-check team codes match the valid list
- Use decimal format for lines (e.g., `265.5` not `265`)
- Create one CSV per week for organization
- Keep your CSVs after running so you can re-run predictions if you update the model
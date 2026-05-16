# Football Match Prediction v1.9

Ein lauffaehiges Python-Projekt fuer Football Match Prediction mit Rolling-xG-Features, ML-Modell und dem v1.9-Regel-Overlay.

- Daten bereinigen: Scores, xG, Datum, Teams
- Features bauen: Form, xG, xGA, Home/Away-Splits, Rest-Days, Marktquoten
- Modell trainieren: Random Forest, Logistic Regression oder Gradient Boosting
- Vorhersagen bewerten: Accuracy, Log Loss, Brier Score, Confusion Matrix
- v1.9-Regelwerk behalten: Kontrollmodell, TDI, Chaos-Score, DNB-Sperren, Away-Favorite-Degradation

> Hinweis: Das Projekt ist Analyse-Software, keine Wettberatung.

## 1. Beginner Installation

Die Core-Installation reicht fuer Tests, Training, eine Einzel-Prediction und eine Fixture-List-Prediction.

```bash
cd football_prediction_v19
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## 2. Full Football Scraping Installation

Wenn du spaeter Scraping-, Notebook- oder Visualisierungs-Extras brauchst:

```bash
python -m pip install -r requirements-full.txt
python -m pip install -e .
```

## 3. Smoke Test

```bash
pytest
```

## 4. Echte Match-Daten Vorbereiten

Lege deine echte historische CSV hier ab:

```text
data/raw/real_matches.csv
```

Nutze als Vorlage:

```text
data/raw/real_matches_template.csv
```

Die Rohdatei braucht diese Spalten:

```text
date,season,league,home_team,away_team,score,home_xg,away_xg,odds_home,odds_draw,odds_away,venue,referee
```

Diese Basis-Spalten reichen aus, damit Vorbereitung, Training und Prediction laufen.

Du kannst das Modell mit optionalen Advanced-Spalten verbessern:

```text
home_xga,away_xga,home_shots,away_shots,home_shots_on_target,away_shots_on_target,home_big_chances,away_big_chances,home_possession,away_possession,home_ppda,away_ppda,home_rest_days,away_rest_days,home_injuries_count,away_injuries_count,home_market_value,away_market_value
```

Wenn diese Spalten vorhanden sind, werden sie in `data/processed/real_matches_clean.csv` behalten und als Rolling Features genutzt. Wenn sie fehlen, laeuft das Projekt weiter mit den Basis-Spalten.

Bereite die Daten dann so vor:

```bash
python -m football_prediction_v19.cli prepare-data --input data/raw/real_matches.csv --output data/processed/real_matches_clean.csv --format auto
```

Oder mit dem Hilfsskript:

```bash
python scripts/prepare_real_data.py
```

Die bereinigte Trainingsdatei landet hier:

```text
data/processed/real_matches_clean.csv
```

`score` darf zum Beispiel `2-1`, `2- 1` oder ein Ergebnis mit Gedankenstrich sein. Spiele ohne Ergebnis werden fuer historische Trainingsdaten entfernt.

### Native Template

Die native Vorlage nutzt direkt die Projektnamen:

```text
data/raw/real_matches_template.csv
```

Import:

```bash
python -m football_prediction_v19.cli prepare-data --input data/raw/real_matches.csv --output data/processed/real_matches_clean.csv --format native
```

### FBref Export

FBref-Style CSVs koennen diese Spalten enthalten:

```text
Date,Season,Comp,Home,Away,Score,xG,xG.1,Venue,Referee
```

Import:

```bash
python -m football_prediction_v19.cli prepare-data --input data/raw/real_matches.csv --output data/processed/real_matches_clean.csv --format fbref
```

Oder mit dem FBref-spezifischen Importer:

```bash
python -m football_prediction_v19.cli import-fbref --input data/raw/fbref_matches.csv --output data/processed/fbref_matches_clean.csv
```

Eine kleine Beispielvorlage liegt hier:

```text
data/raw/fbref_template.csv
```

### football-data.co.uk CSV

football-data CSVs koennen diese Spalten enthalten:

```text
Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A
```

Import:

```bash
python -m football_prediction_v19.cli prepare-data --input data/raw/real_matches.csv --output data/processed/real_matches_clean.csv --format football-data
```

Oder mit dem football-data-spezifischen Importer:

```bash
python -m football_prediction_v19.cli import-football-data --input data/raw/football_data.csv --output data/processed/football_data_clean.csv
```

Eine kleine Beispielvorlage liegt hier:

```text
data/raw/football_data_template.csv
```

### Auto Import And Prepare

Wenn du nicht sicher bist, welches Format deine CSV hat:

```bash
python -m football_prediction_v19.cli import-and-prepare --input data/raw/real_matches.csv --output data/processed/real_matches_clean.csv --format auto
```

Danach kannst du wie gewohnt trainieren, kommende Fixtures vorhersagen und den Excel Report exportieren:

```bash
python -m football_prediction_v19.cli train --input data/processed/real_matches_clean.csv --model models/real_model.joblib --test-season 2023
python -m football_prediction_v19.cli predict-fixtures --history data/processed/real_matches_clean.csv --fixtures data/upcoming_fixtures_template.csv --model models/real_model.joblib --output outputs/predictions.csv
python -m football_prediction_v19.cli export-excel --predictions outputs/predictions.csv --output outputs/predictions_report.xlsx
```

### Team Alias Config

Teamnamen werden beim Import normalisiert. Varianten wie `Man Utd`, `Man United`, `Spurs`, `Wolves` oder `Newcastle` werden ueber diese Datei auf einen Standardnamen gemappt:

```text
config/team_aliases.json
```

Du kannst dort eigene Aliaslisten ergaenzen, damit historische Daten und kommende Fixtures dieselben Teamnamen verwenden.

## 5. Prepare upcoming fixtures

Mit diesem Befehl kannst du eine einfache Roh-CSV mit kommenden Spielen in das Vorhersageformat umwandeln.

Natives Format:

```bash
fpv19 prepare-fixtures --input data/raw/upcoming_fixtures_raw.csv --output data/upcoming_fixtures.csv --format native --default-season 2024 --default-league Bundesliga
```

football-data-Style:

```bash
fpv19 prepare-fixtures --input data/raw/football_data_fixtures.csv --output data/upcoming_fixtures.csv --format football-data --default-season 2024 --default-league Premier-League
```

Der Befehl:

- unterstuetzt natives Format (`home_team`, `away_team`, `date`, ...) und football-data-Style (`HomeTeam`, `AwayTeam`, `Date`, `B365H`, ...)
- normalisiert Teamnamen automatisch (Spurs → Tottenham Hotspur, Man Utd → Manchester United)
- befuellt fehlende optionale Spalten mit sicheren Standardwerten (venue, referee, Quoten, Formation, Fatigue)
- setzt fehlende `season` und `league` aus `--default-season` und `--default-league`
- sortiert nach Datum
- prueft auf fehlende Pflichtfelder (date, home_team, away_team) mit klaren Fehlermeldungen

Vorlagen:

```text
data/raw/upcoming_fixtures_raw_template.csv   (natives Format)
data/raw/football_data_fixtures_template.csv  (football-data-Style)
```

Danach Vorhersage:

```bash
fpv19 predict-fixtures --history data/processed/combined_football_data.csv --fixtures data/upcoming_fixtures.csv --model models/real_model.joblib --output outputs/predictions.csv
```

Danach Excel-Report:

```bash
fpv19 export-excel --predictions outputs/predictions.csv --output outputs/predictions_report.xlsx
```

## 6. Download and prepare football-data.co.uk data

Mit einem einzigen Befehl kannst du CSVs von football-data.co.uk herunterladen und automatisch in trainingsfertige Dateien umwandeln.

Einzelne Liga:

```bash
fpv19 download-prepare-football-data --leagues E0 --seasons 2023 --raw-dir data/raw --processed-dir data/processed
```

Mehrere Ligen und Saisons:

```bash
fpv19 download-prepare-football-data --leagues premier-league bundesliga serie-a --seasons 2022 2023 --raw-dir data/raw --processed-dir data/processed --combine-output data/processed/combined_football_data.csv
```

Der Befehl:

- laedt jede Liga/Saison-Kombination von football-data.co.uk herunter
- speichert Rohdateien unter `--raw-dir` als `football_data_{LIGA}_{SAISON}.csv`
- bereitet jede Datei vor und normalisiert Teamnamen
- speichert bereinigte Dateien unter `--processed-dir` als `football_data_{LIGA}_{SAISON}_clean.csv`
- kombiniert mit `--combine-output` alle Dateien in eine gemeinsame CSV, sortiert nach Datum
- erstellt `raw-dir` und `processed-dir` automatisch

Danach Training:

```bash
fpv19 train --input data/processed/combined_football_data.csv --model models/real_model.joblib --test-season 2023
```

Unterstuetzte Liga-Codes (neben Rohdaten wie `E0`, `D1`):

```text
premier-league, championship, league-one, league-two, national-league,
scottish-premiership, bundesliga, bundesliga-2, serie-a, serie-b,
la-liga, segunda-division, ligue-1, ligue-2, eredivisie,
pro-league, primeira-liga, super-lig, super-league-greece
```

## 7. Modell Trainieren

Mit Sample-Daten:

```bash
python -m football_prediction_v19.cli train --input data/sample_matches.csv --model models/sample_model.joblib --test-season 2023
```

Mit echten vorbereiteten Daten:

```bash
python -m football_prediction_v19.cli train --input data/processed/real_matches_clean.csv --model models/real_model.joblib --test-season 2023
```

## 8. Ein Match Vorhersagen

```bash
python -m football_prediction_v19.cli predict --history data/sample_matches.csv --model models/sample_model.joblib --home Chelsea --away Arsenal --date 2024-05-01 --venue "Stamford Bridge" --referee "Anthony Taylor" --odds-home 2.40 --odds-draw 3.40 --odds-away 2.90
```

## 9. Eine Fixture-Liste Vorhersagen

Nutze die Vorlage in `data/upcoming_fixtures_template.csv` und fuehre dann aus:

```bash
python -m football_prediction_v19.cli predict-fixtures --history data/sample_matches.csv --fixtures data/upcoming_fixtures_template.csv --model models/sample_model.joblib --output outputs/predictions.csv
```

Du kannst die Value-Betting-Schwellen anpassen:

```bash
python -m football_prediction_v19.cli predict-fixtures --history data/sample_matches.csv --fixtures data/upcoming_fixtures_template.csv --model models/sample_model.joblib --output outputs/predictions.csv --min-edge 0.03 --max-chaos 7.0 --min-control 7.0
```

Mit echten historischen Daten und deinem echten Modell:

```bash
python -m football_prediction_v19.cli predict-fixtures --history data/processed/real_matches_clean.csv --fixtures data/upcoming_fixtures_template.csv --model models/real_model.joblib --output outputs/predictions.csv
```

Die CSV-Ausgabe wird automatisch hier angelegt:

```text
outputs/predictions.csv
```

Die Ausgabe enthaelt Modellwahrscheinlichkeiten, Marktquoten, faire Markt-Wahrscheinlichkeiten, Edge-Werte, `value_pick`, `value_edge`, `bet_recommendation` und klare `no_bet_reasons`.

## 10. Excel Report Exportieren

Aus der Prediction-CSV kannst du eine Excel-Datei fuer die Analyse erstellen:

```bash
python -m football_prediction_v19.cli export-excel --predictions outputs/predictions.csv --output outputs/predictions_report.xlsx
```

Die Datei wird hier gespeichert:

```text
outputs/predictions_report.xlsx
```

Sheets im Report:

- `Summary`: Gesamtanzahl Fixtures, empfohlene Bets, No-Bets, Durchschnitts-Edge, Control/Chaos Scores, Top Value Picks und haeufige No-Bet-Gruende.
- `Predictions`: Vollstaendige Matchliste mit Wahrscheinlichkeiten, Quoten, fairen Markt-Wahrscheinlichkeiten, Edges, v1.9 Scores und Flags.
- `Value Bets`: Nur empfohlene Value Bets, nach `value_edge` absteigend sortiert.
- `No Bets`: Spiele, bei denen die Schutzlogik keinen Bet empfiehlt.
- `High Chaos`: Alle Spiele nach `chaos_score` absteigend sortiert.
- `v19 Flags`: Spiele mit aktiven v1.9 Flags.

## 11. Value Betting Und No-Bet Logik

Decimal Odds werden in implied probability umgerechnet:

```text
implied_probability = 1 / decimal_odds
```

Beispiel: Quote `2.00` bedeutet 50 Prozent implied probability. Weil Buchmacher eine Marge einbauen, addieren sich Home/Draw/Away meistens auf mehr als 100 Prozent. Diese Marge heisst Overround. Das Projekt entfernt diese Marge und berechnet faire Markt-Wahrscheinlichkeiten.

Der Value Edge vergleicht Modell gegen fairen Markt:

```text
value_edge = model_probability - fair_market_probability
```

Beispiel: Modell 46 Prozent, fairer Markt 41 Prozent ergibt `+0.05` Edge. Standardmaessig wird ein Value Bet erst ab `--min-edge 0.03` empfohlen.

Die v1.9 Schutzlogik kann trotzdem ein No-Bet setzen:

- kein Value Bet, wenn `control_score < --min-control`
- kein Value Bet, wenn `chaos_score > --max-chaos`
- kein Away Value Bet, wenn Away-Favorite-Degradation aktiv ist
- DNB bleibt gesperrt, wenn die v1.9 DNB-Bedingungen nicht erfuellt sind

Beispiel-Interpretation:

```text
value_pick=Home, value_edge=0.052, bet_recommendation="Value bet: Home 1X2"
```

Das bedeutet: Das Modell sieht Home um 5.2 Prozentpunkte staerker als der margengefilterte Markt, und die v1.9 Schutzregeln blockieren den Tipp nicht.

## 12. Betting Backtest Und Calibration Report

Wenn du ein trainiertes Modell und historische Daten mit Ergebnissen und Quoten hast, kannst du die Value-Bet-Regeln historisch testen:

```bash
python -m football_prediction_v19.cli backtest-bets --history data/processed/real_matches_clean.csv --model models/real_model.joblib --output outputs/backtest_bets.csv --report outputs/backtest_report.md --min-edge 0.03 --max-chaos 7.0 --min-control 7.0
```

Die CSV `outputs/backtest_bets.csv` enthaelt jede historische Partie, Modellwahrscheinlichkeiten, faire Markt-Wahrscheinlichkeiten, Edge, Bet-Entscheidung, Stake, Profit und kumulierten Profit.

Der Report `outputs/backtest_report.md` fasst zusammen:

- total matches, total bets und no-bet count
- hit rate, total profit, ROI und yield
- average edge
- Performance nach Pick-Typ und Liga
- groesste Gewinner und Verlierer
- haeufigste No-Bet-Gruende
- Brier score, Log Loss und Overconfidence-Warnung

ROI und Yield werden hier als Profit geteilt durch eingesetzte Units gelesen. Beispiel: `+8.0%` bedeutet, dass pro 100 eingesetzten Units historisch 8 Units Profit entstanden waeren.

Ein profitabler Backtest garantiert keinen zukuenftigen Profit. Er zeigt nur, wie diese Modellversion mit diesen Daten und diesen Regeln historisch abgeschnitten haette.

## 13. Alles in Einem Schritt

Das Projekt enthaelt auch ein Hilfsskript:

```bash
python scripts/run_all.py
```

Dieses Skript trainiert das Beispielmodell, fuehrt eine Einzel-Prediction aus, schreibt eine Fixture-List-Prediction nach `outputs/predictions.csv` und exportiert `outputs/predictions_report.xlsx`.

## 14. Projektstruktur

```text
football_prediction_v19/
|-- data/
|   |-- raw/
|   |-- processed/
|-- docs/
|-- models/
|-- outputs/
|-- scripts/
|-- src/football_prediction_v19/
`-- tests/
```

Wichtige Module, die bewusst erhalten bleiben:

- `data.py`
- `features.py`
- `model.py`
- `rules_v19.py`
- `backtest.py`
- `cli.py`

## 15. Wie Das Modell Arbeitet

1. Historische Spiele werden bereinigt.
2. Pro Match werden nur vorherige Spiele genutzt, damit kein Data Leakage entsteht.
3. Rolling-Features fuer Form, Tore, xG und xGA werden gebaut.
4. Das Modell lernt die Klassen `H`, `D`, `A`.
5. Die Modellwahrscheinlichkeiten werden durch das v1.9-Regelwerk gefiltert.
6. Das Ergebnis enthaelt Wahrscheinlichkeiten, Empfehlungen, Sperren und No-Bet-Signale.



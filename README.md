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

Bereite die Daten dann so vor:

```bash
python -m football_prediction_v19.cli prepare-data --input data/raw/real_matches.csv --output data/processed/real_matches_clean.csv
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

## 5. Modell Trainieren

Mit Sample-Daten:

```bash
python -m football_prediction_v19.cli train --input data/sample_matches.csv --model models/sample_model.joblib --test-season 2023
```

Mit echten vorbereiteten Daten:

```bash
python -m football_prediction_v19.cli train --input data/processed/real_matches_clean.csv --model models/real_model.joblib --test-season 2023
```

## 6. Ein Match Vorhersagen

```bash
python -m football_prediction_v19.cli predict --history data/sample_matches.csv --model models/sample_model.joblib --home Chelsea --away Arsenal --date 2024-05-01 --venue "Stamford Bridge" --referee "Anthony Taylor" --odds-home 2.40 --odds-draw 3.40 --odds-away 2.90
```

## 7. Eine Fixture-Liste Vorhersagen

Nutze die Vorlage in `data/upcoming_fixtures_template.csv` und fuehre dann aus:

```bash
python -m football_prediction_v19.cli predict-fixtures --history data/sample_matches.csv --fixtures data/upcoming_fixtures_template.csv --model models/sample_model.joblib --output outputs/predictions.csv
```

Mit echten historischen Daten und deinem echten Modell:

```bash
python -m football_prediction_v19.cli predict-fixtures --history data/processed/real_matches_clean.csv --fixtures data/upcoming_fixtures_template.csv --model models/real_model.joblib --output outputs/predictions.csv
```

Die CSV-Ausgabe wird automatisch hier angelegt:

```text
outputs/predictions.csv
```

## 8. Alles in Einem Schritt

Das Projekt enthaelt auch ein Hilfsskript:

```bash
python scripts/run_all.py
```

Dieses Skript trainiert das Beispielmodell, fuehrt eine Einzel-Prediction aus und schreibt danach eine Fixture-List-Prediction nach `outputs/predictions.csv`.

## 9. Projektstruktur

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

## 10. Wie Das Modell Arbeitet

1. Historische Spiele werden bereinigt.
2. Pro Match werden nur vorherige Spiele genutzt, damit kein Data Leakage entsteht.
3. Rolling-Features fuer Form, Tore, xG und xGA werden gebaut.
4. Das Modell lernt die Klassen `H`, `D`, `A`.
5. Die Modellwahrscheinlichkeiten werden durch das v1.9-Regelwerk gefiltert.
6. Das Ergebnis enthaelt Wahrscheinlichkeiten, Empfehlungen, Sperren und No-Bet-Signale.

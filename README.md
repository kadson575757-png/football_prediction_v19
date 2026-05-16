# Football Match Prediction v1.9

Ein lauffaehiges Python-Projekt fuer Football Match Prediction mit Rolling-xG-Features, ML-Modell und dem v1.9-Regel-Overlay.

- Daten bereinigen: Scores, xG, Datum, Teams
- Features bauen: Form, xG, xGA, Home/Away-Splits, Rest-Days, Marktquoten
- Modell trainieren: Random Forest, Logistic Regression oder Gradient Boosting
- Vorhersagen bewerten: Accuracy, Log Loss, Brier Score, Confusion Matrix
- v1.9-Regelwerk behalten: Kontrollmodell, TDI, Chaos-Score, DNB-Sperren, Away-Favorite-Degradation

> Hinweis: Das Projekt ist Analyse-Software, keine Wettberatung.

## 1. Beginner Installation

Die Core-Installation reicht fuer Tests, Training und eine Beispiel-Prediction.

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

## 4. Sample Model Trainieren

```bash
python -m football_prediction_v19.cli train --input data/sample_matches.csv --model models/sample_model.joblib --test-season 2023
```

## 5. Sample Prediction

```bash
python -m football_prediction_v19.cli predict --history data/sample_matches.csv --model models/sample_model.joblib --home Chelsea --away Arsenal --date 2024-05-01 --venue "Stamford Bridge" --referee "Anthony Taylor" --odds-home 2.40 --odds-draw 3.40 --odds-away 2.90
```

## 6. Alles in Einem Schritt

Das Projekt enthaelt auch ein Hilfsskript:

```bash
python scripts/run_all.py
```

Dieses Skript trainiert das Beispielmodell und fuehrt danach direkt eine Beispiel-Prediction aus.

## 7. Eigene Daten

Mindestens diese Spalten werden erwartet:

```text
Date,Wk,Home,Away,xG,xG.1,Score,Venue,Referee
```

Optional, aber hilfreich:

```text
odds_home,odds_draw,odds_away,attendance
```

`Score` darf zum Beispiel `2-1`, `2–1` oder `2- 1` sein. `xG` ist Home-xG, `xG.1` ist Away-xG.

## 8. Projektstruktur

```text
football_prediction_v19/
|-- data/
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

## 9. Wie das Modell arbeitet

1. Historische Spiele werden bereinigt.
2. Pro Match werden nur vorherige Spiele genutzt, damit kein Data Leakage entsteht.
3. Rolling-Features fuer Form, Tore, xG und xGA werden gebaut.
4. Das Modell lernt die Klassen `H`, `D`, `A`.
5. Die Modellwahrscheinlichkeiten werden durch das v1.9-Regelwerk gefiltert.
6. Das Ergebnis enthaelt Wahrscheinlichkeiten, Empfehlungen, Sperren und No-Bet-Signale.

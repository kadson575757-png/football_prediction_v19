# Dixon-Coles Findings - La Liga 2023-2024

## Ergebnisse
- Home Accuracy: 69.5% (ML: ~71%) - DC leicht schlechter
- BTTS Accuracy: 49.5% (ML: 65.5%) - DC strukturell unterlegen
- Under35 Accuracy: 72.4% (ML: ~71%) - DC minimal besser

## Ursache BTTS-Schwaeche
- Mean DC BTTS prob: 0.274 vs Actual rate: 0.500
- DC probs > 0.5: nur 1.4% aller Spiele
- Strukturell: Poisson-Unabhaengigkeitsannahme unterschaetzt
  Korrelation zwischen Home/Away Goals in La Liga

## Verwendung
- DC NICHT fuer: BTTS, BOTH_OVER25_BTTS
- DC JA fuer: Under_35, Over_25 als Confirmation Layer
- DC NEUTRAL: 1X2 Direction

## Naechster Schritt
Phase 5 Feature Engineering - Elo + H2H + Time Decay
Ziel: ML-BTTS von 65.5% durch bessere Features verbessern

# Priority Watchlist Rules

## Tier-Hierarchie (Stand Phase 3)

A_TIER (Score >= 85) und B_TIER (Score >= 65) sind gleichrangig
in der Priority Watchlist. B_TIER historisch stärker als A_TIER
(77.9% vs 74.7% in 2024/25 Aggregate).

## Automatische Downgrades

- A_TIER → B_TIER wenn Score < 85 (Mindest-Schwelle nicht erreicht)
- A_TIER → B_TIER wenn `league_warning_flags` aktiv
- A_TIER → B_TIER für alle Ligue 1 Spiele (55.9% A_TIER historisch)

## Permanente Sperren

- BOTH_OVER25_BTTS: immer HARD_NO_GO (48.7% historisch)

## Subtype-Empfehlungen

Bevorzugt: UNDER_35, DOUBLE_CHANCE_1X, DOUBLE_CHANCE_X2
Gemieden:  BTTS, BOTH_OVER25_BTTS, OVER_25

# MLS Control Score vs Total Goals — Diagnostic Audit

> DIAGNOSTIC ONLY — no betting recommendations. No live betting claims.
> Generated: 2026-05-17

---

## Today's Observation (trigger for this audit)

| Match | Control | Chaos | Total Goals |
|---|---:|---:|---:|
| Seattle vs LA Galaxy | 7.56 | 2.00 | 2 |
| Real Salt Lake vs Colorado | 6.52 | 3.05 | 3 |
| San Diego vs Cincinnati | 5.12 | 4.00 | 6 |
| San Jose vs Dallas | 3.60 | 5.47 | 5 |

Apparent pattern: lower control = more goals. Is this real historically?

---

## Season 2024 (n=522, OOS test season)

| Bucket | N | Avg Goals | O1.5% | O2.5% | O3.5% | BTTS% | H% | D% | A% | Avg Control |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| control < 4.0 | 49 | 2.80 | 73.5% | 53.1% | 34.7% | 53.1% | 51.0% | 22.4% | 26.5% | 3.60 |
| 4.0 <= control < 5.5 | 122 | 2.71 | 77.0% | 49.2% | 35.2% | 68.0% | 32.0% | 53.3% | 14.8% | 4.75 |
| 5.5 <= control < 7.0 | 134 | 2.99 | 79.9% | 56.0% | 36.6% | 64.2% | 38.1% | 35.8% | 26.1% | 6.24 |
| control >= 7.0 | 217 | 3.49 | 87.1% | 73.7% | 41.5% | 61.3% | 55.3% | 2.3% | 42.4% | 7.87 |

Correlation 2024:
- Control vs Total Goals: Pearson r=+0.194 (p<0.001***), Spearman r=+0.187
- Chaos vs Total Goals: Pearson r=-0.145 (p<0.001***), Spearman r=-0.146

---

## Season 2025 (n=539, OOS test season)

| Bucket | N | Avg Goals | O1.5% | O2.5% | O3.5% | BTTS% | H% | D% | A% | Avg Control |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| control < 4.0 | 44 | 3.34 | 81.8% | 63.6% | 45.5% | 61.4% | 47.7% | 34.1% | 18.2% | 3.59 |
| 4.0 <= control < 5.5 | 133 | 2.80 | 75.2% | 53.4% | 29.3% | 57.1% | 44.4% | 25.6% | 30.1% | 4.72 |
| 5.5 <= control < 7.0 | 134 | 3.04 | 80.6% | 58.2% | 36.6% | 61.2% | 42.5% | 22.4% | 35.1% | 6.31 |
| control >= 7.0 | 228 | 3.07 | 78.1% | 61.4% | 37.3% | 60.1% | 44.7% | 24.6% | 30.7% | 7.79 |

Correlation 2025:
- Control vs Total Goals: Pearson r=+0.014 (p=ns), Spearman r=+0.035
- Chaos vs Total Goals: Pearson r=-0.054 (p=ns), Spearman r=-0.063

---

## Combined 2024 + 2025 (n=1,061)

| Bucket | N | Avg Goals | O2.5% | O3.5% | BTTS% | H% | D% | A% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| control < 4.0 | 93 | 3.05 | 58.1% | 39.8% | 57.0% | 49.5% | 28.0% | 22.6% |
| 4.0 <= control < 5.5 | 255 | 2.76 | 51.4% | 32.2% | 62.4% | 38.4% | 38.8% | 22.7% |
| 5.5 <= control < 7.0 | 268 | 3.01 | 57.1% | 36.6% | 62.7% | 40.3% | 29.1% | 30.6% |
| control >= 7.0 | 445 | 3.27 | 67.4% | 39.3% | 60.7% | 49.9% | 13.7% | 36.4% |

Overall correlation (all MLS, n=2,056):
- Control vs Total Goals: Pearson r=+0.089 (p<0.001***), Spearman r=+0.089
- Chaos vs Total Goals: Pearson r=-0.073 (p<0.001***), Spearman r=-0.071

---

## Key Findings

### 1. The observed pattern is INVERTED vs the hypothesis

Today's 4 games suggested: lower control = more goals.
The historical data shows the OPPOSITE:

- control >= 7.0 has the HIGHEST O2.5% in both seasons (73.7% in 2024, 61.4% in 2025)
- control < 4.0 has the lowest O2.5% in 2024 (53.1%) and mid-range in 2025 (63.6%)
- Average goals are highest in control >= 7.0 (3.49 in 2024, 3.07 in 2025)

The correlation sign is POSITIVE (r=+0.089 to +0.194): higher control correlates
with MORE goals, not fewer.

### 2. The 2024 signal is statistically significant; 2025 is not

| Season | Pearson r | p-value | Significant? |
|---|---:|---:|---|
| 2024 | +0.194 | p<0.001 | Yes *** |
| 2025 | +0.014 | p=0.75 | No (ns) |
| All MLS | +0.089 | p<0.001 | Yes *** |

The 2025 correlation is essentially zero. The aggregate significance is driven mostly
by 2024 and the earlier training seasons.

### 3. Today's 4-game observation was noise

With n=4, any apparent pattern has no statistical power. Today's games happen to
show the visual inverse of the historical average, but both directions are within the
normal variance of a 4-game sample.

### 4. What is actually in the "low control" bucket?

control < 4.0 rows in 2024-2025 (n=93) have:
- Draw rate: 28.0% - higher than mid-range buckets
- Away win rate: 22.6% - the LOWEST of all buckets
- Home win rate: 49.5%

Low-control games are contested/uncertain matches, not goal-fests.
The model has low conviction, draws are elevated, away wins depressed.

### 5. Chaos score relationship

Chaos shows a NEGATIVE correlation with goals (r=-0.073): higher chaos is associated
with slightly fewer goals. Chaotic/uncertain matches tend toward lower-scoring draws.

---

## Paper-Test Verdict

NOT RECOMMENDED based on this audit.

1. The direction of the signal is INVERTED from the hypothesis.
2. The 2025 correlation is statistically zero - no replication.
3. Over 2.5 odds for low-control games are not in the dataset - ROI cannot be computed.
4. The highest O2.5% bucket is HIGH-control (>=7.0, 67.4% combined, 73.7% in 2024).

SEPARATE SIGNAL WORTH WATCHING: Over 2.5 in high-control (>=7.0) games.
- Combined O2.5 = 67.4% (n=445)
- 2024 O2.5 = 73.7% (n=217) - very high
- 2025 O2.5 = 61.4% (n=228) - does not replicate at the same level
- Needs Over 2.5 market odds to compute ROI before any paper-test consideration.

> DIAGNOSTIC ONLY. No betting recommendations. No live betting.
> Minimum 100 tracked bets required before evaluating any new signal.

# Scoring policy

`scoring-v1` is deterministic. A score of 6 or higher is qualified; a lower
score is rejected. Unknown signals contribute zero and no hard override changes
the arithmetic.

| Signal | Points |
| --- | ---: |
| Reservations explicitly require calling | +3 |
| No online booking path or provider found | +2 |
| Private dining or events offered | +2 |
| Catering offered | +2 |
| Two or more locations | +2 |
| Phone heavily promoted | +1 |
| Complicated or split hours | +1 |
| Large FAQ or menu | +1 |
| High-ticket menu | +1 |
| No public contact route | -3 |
| Permanently closed | -3 |
| Fast-food or low-ticket positioning | -2 |

Every awarded or denied component records its state, explanation, delta, and
evidence IDs. Absence-based signals remain unknown unless the allowed crawl is
complete.

# Science review 2026-08-09

Run: `outputs/production`
Config: `configs/production.yaml`
production_verification: PASS
**science_review_status: PASS**

## L0 mechanical
- pass: True
- hard_fail_count: 0 / 3
- soft_rates: {"S1_topic_align": 1.0, "S2_property_cue": 1.0, "S3_claim_quote": 1.0, "S4_actionability": 1.0}

| gap_id | hard_ok | issues |
|--------|---------|--------|
| gap-missing-link-topic | True | — |
| gap-limitations | True | — |
| gap-temporal-SnSe | True | — |

## L1 AI dual-role sample
- pass: True
- keep/revise/reject: 2/1/0 (keep_rate=0.6667)
- seed: 42

| gap_id | decision | total | notes |
|--------|----------|-------|-------|
| gap-missing-link-topic | revise | 8 | novelty_honesty: A=1 B=0 -> 0 |
| gap-limitations | keep | 10 | — |
| gap-temporal-SnSe | keep | 10 | — |

Overall: accept

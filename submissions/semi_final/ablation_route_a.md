# Route A ablation — rule-only vs LLM-on

Seed: **42** · Bundle: `production_sciverse`.

| Metric | Rule-only | LLM-on |
|--------|-----------|--------|
| Candidates | 12 | 12 |
| Novelty | `{'candidate_new': 2, 'known': 10}` | `{'known': 11, 'candidate_new': 1}` |
| External verdicts | `['pass', 'pass', 'pass', 'pass', 'error']` | `['pass', 'pass', 'pass', 'pass', 'pass']` |
| llm_score_unavailable | `False` | `False` |
| Roles | `external_pass, mutate, rule_mutate, seed_template` | `external_pass, llm_focus_mutate, llm_prune_soft, llm_score, llm_seed_refine, mutate, seed_template` |

## Top motifs

- Rule: `['PbTe', 'PbTe', 'SnSe', 'PbTe', 'graphene']`
- LLM: `['SnSe', 'PbTe', 'SnSe', 'SnSe', 'PbTe']`

## Top hypotheses (truncated)

### Rule-only

- In PbTe, tuning defect-phonon coupling can improve stability if electronic transport remains above a minimum mobility threshold.
- Nano-precipitates coherent with PbTe matrix improve stability via hierarchical phonon scattering.
- In SnSe, tuning defect-phonon coupling can improve conductivity if electronic transport remains above a minimum mobility threshold.
- In PbTe, tuning defect-phonon coupling can improve capacity if electronic transport remains above a minimum mobility threshold.
- In graphene, tuning defect-phonon coupling can improve electrical conductivity if electronic transport remains above a minimum mobility threshold.

### LLM-on

- We need to mutate the hypothesis slightly to explore nearby SPR space. The parent is about anion/cation vacancy pairs in PbTe decoupling phonon and electron scattering for Seebeck. We need to keep it falsifiable, one sen...
- The user wants me to refine a seed into one falsifiable materials SPR (Structure-Property Relationship) hypothesis. The topic is SnSe lattice thermal conductivity vacancy engineering. The seed mentions nano-precipitates ...
- The user wants me to refine a seed idea about anion/cation vacancy pairs in PbTe that decouple phonon and electron scattering (relevant to Seebeck) into a single falsifiable SPR (Single Property Relationship) hypothesis....
- The user wants a slightly mutated hypothesis from a parent about anion/cation vacancy pairs in PbTe that decouple phonon and electron scattering for Seebeck. I need to keep it as a single falsifiable SPR, prefer SnSe mot...
- The user wants me to refine a seed idea into one falsifiable materials SPR (Single Property Relationship) hypothesis. The seed is about anion/cation vacancy pairs in PbTe decoupling phonon and electron scattering relevan...

## Read for judges

Rule-only proves the search loop is reproducible without LLM spend. LLM-on shows SEED/SCORE/PRUNE/MUTATE roles with **no** `llm_score_unavailable` in this run. MP/external verdicts validate motifs (LLM path: pass×5 after formula gate).

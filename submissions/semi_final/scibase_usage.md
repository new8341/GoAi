# Sci-Base 使用证明

> Dataset: https://huggingface.co/datasets/opendatalab/Sci-Base

## 接入方式

- Retriever: `backend: scibase` / hybrid `sciverse_scibase`
- Cache: `data/scibase/materials_cache.jsonl`（自 HF `paper` split 流式扫描构建）
- Cache rows: **80**
- Build: `py -3 scripts/build_scibase_cache.py --max-scan 1500 --max-keep 80`

## 主题检索抽样

- `091c8560177d533a788c` | score=0.0843 | Assembly‐Free Fabrication of High‐Performance Flexible Inorganic Thin‐Film Thermoelectric Device Prepared by a Thermal Diffusion
  - doi: `10.1002/aenm.202202731`
  - source label: `scibase` → evidence `retrieval_database=scibase`
- `b30669276b62a68a9d46` | score=0.0843 | Analytical solution for the steady states of the driven Hubbard model
  - doi: `10.1103/physrevb.103.035146`
  - source label: `scibase` → evidence `retrieval_database=scibase`
- `156a6ca3157ff8be4633` | score=0.0843 | Chip-scale solar thermal electrical power generation
  - doi: `10.1016/j.xcrp.2022.100789`
  - source label: `scibase` → evidence `retrieval_database=scibase`
- `fba3ed3d3076d214fb87` | score=0.0843 | Aluminosilicate Nanocomposites from Incinerated Chinese Holy Joss Fly Ash: A Potential Nanocarrier for Drug Cargos
  - doi: `10.1038/s41598-020-60208-x`
  - source label: `scibase` → evidence `retrieval_database=scibase`
- `4135d4dbeedc87e5b21e` | score=0.0843 | Development of Metallo (Calcium/Magnesium) Polyurethane Nanocomposites for Anti-Corrosive Applications
  - doi: `10.3390/ma15238374`
  - source label: `scibase` → evidence `retrieval_database=scibase`

## 合规

- 结构/解析格式：CC-BY-4.0；正文保留原 OA 许可。
- 全库 TB 级：竞赛路径使用材料子集缓存，不下载整库。

## Gold hybrid run (Docker + GROBID)

- Profile: `configs/production_sciverse_scibase.yaml`
- Output: `outputs/production_sciverse_scibase/`
- `verify_production`: **PASS**
- Papers: sciverse + scibase in same batch (Database column shows `scibase`)
- Report: `report.pdf` / `.tex` / `.bib` regenerated


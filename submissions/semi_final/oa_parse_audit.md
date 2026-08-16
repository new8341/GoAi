# OA fulltext parse audit (production_sciverse)

Papers: **5**; parser-derived with `pdf_hash`: **3/5**.

| Paper | fulltext_source | has_pdf_hash | note |
|-------|-----------------|--------------|------|
| `SV-paper_10.1021_acs.jpcc.2c02401` | `grobid` | `True` | parsed OK |
| `SV-paper_10.1002_aenm.201803242` | `grobid` | `True` | parsed OK |
| `SV-paper_10.1088_2632-959x_abd291` | `grobid` | `True` | parsed OK |
| `SV-paper_10.1021_acsaenm.5c00559` | `none` | `False` | no OA parse / unreachable / not used as production evidence |
| `SV-paper_10.1021_acsnano.1c01469` | `none` | `False` | no OA parse / unreachable / not used as production evidence |

## Counts

- source histogram: `{'grobid': 3, 'none': 2}`

Semi-final policy: raise parsed ratio via legal OA mirrors only, or document each miss (403 / no-OA / parse fail). Never scrape paywalls or claim abstract as production fulltext.

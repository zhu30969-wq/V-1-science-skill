# Validation methodology

## Why the source chain exists

LLMs memorize plausible-looking equations. Science requires that every
equation traces to an authoritative source, was transcribed under explicit
conventions, passed deterministic unit/dimension checks, reproduced a known
limiting case, and is covered by a unit test. Anything less is a
CANDIDATE_MODEL — useful for exploration, invalid for production claims.

## Platform mapping

| Chain step | Platform mechanism |
|---|---|
| Primary source | `source_ids` on Equation/Ontology entries |
| Reference record | skills/*/references/*.md |
| Convention | `physics/conventions.py` registry |
| Transcription | Equation.symbolic_form (SymPy-parsable) |
| Unit/dim check | `validators/units.py`, `validators/dimensions.py` |
| Limiting case | unit tests in `platform/tests/physics/` |
| Production | Equation.status == VALIDATED |

## Statuses that exist

VALIDATED, CANDIDATE_MODEL. There is no PROVEN. Claims top out at
SUPPORTED_WITHIN_SCOPE, and only the Scientific Judge assigns that.

## Sources

- Chong et al., Nature Photonics 14, 350 (2020)
- Goodman, Introduction to Fourier Optics, 4th ed. (2017)
- Voelz, Computational Fourier Optics (2011)
- Andrews & Phillips, Laser Beam Propagation through Random Media (2005)
- Lane et al., Waves in Random Media 2, 209 (1992)

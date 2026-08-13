# ARCHITECTURE.md — STOV AI Scientist

## System architecture

```mermaid
flowchart TD
    User[Human Researcher] --> Pages[GitHub Pages Static Frontend]
    Pages -->|NEXT_PUBLIC_GATEWAY_URL only| GW[Secure Gateway]
    GW -->|server-side x-api-key| Server[LangGraph Agent Server]
    Server --> RG[ResearchGraph]
    RG --> W[Deep Agent Workers]
    RG --> V[Deterministic Validators]
    RG --> HG[Human Gates]
    W --> SK[Scientific Skills]
    SK --> Core[Scientific Compute]
    Core --> AE[Artifact + Evidence]
    RG --> Sim[Simulation Harness]
    Sim --> Core
    RG --> J[Scientific Judge]
    J --> AB[Audit Bundle]
    Server --> DS[DeepSeek API]
```

Layer responsibilities (spec §2):

| Layer | Responsibility |
|---|---|
| LangGraph | Scientific Control Plane — decides when to call which worker |
| Deep Agents | bounded long-horizon research workers (literature, hypothesis, mechanism, counterexample, synthesis) |
| Scientific Skills | capabilities (K-Dense upstream skills + stov-* domain skills) |
| Pydantic | scientific contracts (schemas/) |
| SymPy / Pint / NumPy / SciPy | deterministic validation + compute |
| LangSmith | tracing + evaluation + deployment |
| GitHub Pages | STATIC web frontend ONLY — no secrets, ever |
| Gateway | secure browser/backend boundary (secret holder) |
| DeepSeek | LLM provider (DEEPSEEK_API_KEY only) |

## ResearchGraph

```mermaid
flowchart LR
    IN[research_intake] --> SG[scope_gate HUMAN]
    SG --> PF[problem_formalization] --> ON[initial_ontology]
    ON --> LR2[literature_research] --> EX[evidence_extraction]
    EX --> OR[ontology_refinement] --> GA[gap_analysis]
    GA --> HYP[hypothesis_generation] --> RIV[rival_generation]
    RIV --> PR[prediction_derivation] --> HG[hypothesis_gate HUMAN]
    HG --> ME[mechanism_exploration] --> MR[model_route_selector]
    MR --> MOD[analytical/numerical model] --> AS[model_assembly]
    AS --> VG[validation_graph] --> MG[model_gate]
    MG --> SP[simulation_planning] --> SL[solver_selection]
    SL --> SG2[simulation_graph] --> OB[observable_extraction]
    OB --> CX[counterexample_search] --> CG[contradiction_evaluation]
    CG --> EU[evidence_update] --> CS[claim_synthesis]
    CS --> SJ[scientific_judge] --> FG[final_claim_gate HUMAN]
    FG --> AU[audit_bundle]
```

Human gates: SCOPE, HYPOTHESIS_DIRECTION, FINAL_CLAIM — LangGraph
`interrupt()` with APPROVE / EDIT / REJECT + resume.

## ValidationGraph / SimulationGraph / ContradictionGraph

```mermaid
flowchart TD
    subgraph Validation
        VM[validate_model] -->|fail + revisions left| RM[revise model]
        VM -->|fail + exhausted| HR[HUMAN_REVIEW_REQUIRED]
        VM -->|pass| OK[pass]
    end
    subgraph Simulation
        RS[run_simulation] -->|failure| CL[classify] -->|RERUN + retries left| RS
        CL -->|exhausted| HR2[HUMAN_REVIEW_REQUIRED]
        RS -->|completed| DONE[done]
    end
    subgraph Contradiction
        CC[classify] --> RT[route: fix_numerical / redesign_sampling /
            revise_model_domain / evidence_review /
            model_hypothesis_review / additional_test_or_human]
    end
```

## Scientific integrity architecture

- LLM output lands in Pydantic contracts before entering any graph edge.
- Validator order: Schema → Units → Dimensions → Symbols → Limits →
  Boundary → Topology → Sampling → Physics.
- All loops bounded by AcceptancePolicy; exceeding a bound →
  HUMAN_REVIEW_REQUIRED.
- Numerical failure ≠ physical contradiction; search failure ≠
  "no literature exists"; INCONCLUSIVE is a valid outcome.
- Every claim traces: Claim → Evidence → Model → Simulation → Parameters →
  Code → Git Commit → Environment (audit bundle + SHA256 artifacts).

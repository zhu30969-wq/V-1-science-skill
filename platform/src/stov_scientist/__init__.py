"""STOV AI Scientist — scientific control plane for Space-Time Optical Vortex research.

Layering (per ARCHITECTURE.md):

    LangGraph           = Scientific Control Plane
    Deep Agents         = bounded long-horizon research workers
    Scientific Skills   = scientific capabilities (K-Dense upstream + stov-* domain skills)
    Pydantic            = scientific contracts
    SymPy/Pint/NumPy    = deterministic validation + compute
    LangSmith           = tracing + evaluation + deployment
"""

__version__ = "0.1.0"

# Campaigns

Each research campaign lives in `campaigns/<campaign_id>/`:

```
campaigns/<campaign_id>/
├── campaign.json       # ResearchCampaign + AcceptancePolicy + human decisions
├── state/              # durable scientific objects (survive interrupts/resume)
└── audit/              # the audit bundle (spec §48)
```

Domain-specific STOV campaigns (e.g. `2026-001`) belong here; the platform
itself stays generic STOV infrastructure.

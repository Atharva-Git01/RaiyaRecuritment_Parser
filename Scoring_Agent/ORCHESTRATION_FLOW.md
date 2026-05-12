          │ APPROVED        │ REJECTED
          ▼                 ▼
┌─────────────────────────┐  ┌─────────────────┐
│ STATE: RAG_VALIDATION   │  │  STATE: FAILED  │
│  ┌──────────────────┐   │  │  Store Error    │
│  │ RAG Validation   │   │  └─────────────────┘
│  │ Layer            │   │
│  │ • Semantic Check │   │
│  │ • Ground Truth   │   │
│  │ • Evidence Gen   │   │
│  └──────────────────┘   │
└────────┬────────────────┘
          │                 │
          │ PASSED          │ FAILED
          ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│ STATE: COMPLETED│  │  STATE: FAILED  │
│ Success = True  │  │  Store Error    │
└────────┬────────┘  └─────────────────┘
          │
          ▼
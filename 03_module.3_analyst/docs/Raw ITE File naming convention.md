**Raw ITE File naming convention**:



{lastname}\_{firstname}\_{YYYY}\_blueprint.pdf

{lastname}\_{firstname}\_{YYYY}\_bodysystem.pdf

{lastname}\_{firstname}\_{YYYY}\_score.pdf


**ITE analysis directory structure / file map**:





ITE\_{lastname}\_{firstname}/

&#x20; inputs/

&#x20;   {lastname}\_{firstname}\_{YYYY}\_blueprint.pdf

&#x20;   {lastname}\_{firstname}\_{YYYY}\_bodysystem.pdf

&#x20;   {lastname}\_{firstname}\_{YYYY}\_score.pdf

&#x20; outputs/                          ← always pass this as --output-dir

&#x20;   analysis\_v2\_2024.json           ← auto-generated, one per year run

&#x20;   analysis\_v2\_2025.json

&#x20;   ITE\_2024\_v3\_Analysis\_...docx

&#x20;   ITE\_2025\_v3\_Analysis\_...docx



=================================================================================================================================----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------=================================================================================================================================





board\_prep\_intel/                                   ← PROJECT ROOT

│

├── 00\_database/

│   └── db/

│       └── ite\_intelligence.db                     ← source of truth, never disposable

│

├── 01\_module.1\_warehouse/

│   ├── citation\_files/

│   │   ├── ITE/  (VC\_fail / VC\_pass / local\_lite / right\_click)

│   │   └── AAFP/

│   └── ite\_exams/  (2018–2025 MC + critique PDFs)

│

├── 02\_module.2\_processor/

│   └── scripts/  (extraction, enrichment pipeline)

│

├── 03\_module.3\_analyst/

│   ├── scripts/

│   │   ├── ite\_analyze\_v2.py                       ← pipeline orchestrator

│   │   ├── ite\_analyzer\_v3.py                      ← analysis engine

│   │   ├── ite\_report\_builder\_v2.js                ← DOCX generator

│   │   ├── abfm\_reference\_2024.json                ← national benchmarks by year

│   │   └── abfm\_reference\_2025.json

│   │

│   └── resident\_data/

│       │

│       ├── ITE\_pjetergjoka\_adona/                  ← one folder per resident, forever

│       │   ├── inputs/                             ← raw ABFM PDFs go here

│       │   │   ├── pjetergjoka\_adona\_2024\_blueprint.pdf

│       │   │   ├── pjetergjoka\_adona\_2024\_bodysystem.pdf

│       │   │   ├── pjetergjoka\_adona\_2024\_score.pdf

│       │   │   ├── pjetergjoka\_adona\_2025\_blueprint.pdf

│       │   │   ├── pjetergjoka\_adona\_2025\_bodysystem.pdf

│       │   │   └── pjetergjoka\_adona\_2025\_score.pdf

│       │   │

│       │   └── outputs/                            ← pass as --output-dir every run

│       │       ├── analysis\_v2\_2024.json           ← YoY source for next year's run

│       │       ├── analysis\_v2\_2025.json

│       │       ├── score\_analysis\_2024.json

│       │       ├── score\_analysis\_2025.json

│       │       ├── ITE\_2024\_v3\_Analysis\_Adona\_Pjetergjoka.docx

│       │       ├── ITE\_2024\_v3\_Exam\_Adona\_Pjetergjoka.docx

│       │       ├── ITE\_2025\_v3\_Analysis\_Adona\_Pjetergjoka.docx

│       │       └── ITE\_2025\_v3\_Exam\_Adona\_Pjetergjoka.docx

│       │

│       ├── ITE\_scholl\_michael/

│       │   ├── inputs/

│       │   └── outputs/

│       │

│       └── ITE\_sarkar\_arghyadeep/

│           ├── inputs/

│           └── outputs/

│

├── 04\_module.4\_sandbox/

├── 05\_module.5\_web/

└── key\_data\_files/

&#x20;   └── session\_hy\_inserts\_v7.json                  ← VC gate (352 citations)










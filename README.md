# Career Wiki Pipeline

An automated pipeline that builds a comprehensive career encyclopedia from public labor data. It pulls occupation data from O\*NET and BLS, enriches each career with AI-generated content, publishes wiki-style pages to Azure Blob Storage, runs dual-model quality review, and produces both styled HTML pages and an interactive career relationship graph.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 1 — Data Acquisition                                        │
│                                                                     │
│  prepare_data.py ──→ trim_data.py ──→ final_data.json (3,300)      │
│  (O*NET + BLS)       (filter/rank)                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  Phase 2 — Content Generation                                       │
│                                                                     │
│  final_data.json ──→ pipeline.py ──→ Azure Blob Storage             │
│                      (Gemini API)     careers/*.md                   │
│                                                                     │
│                      update_pipeline.py (force-overwrite mode)       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  Phase 3 — Quality Review                                           │
│                                                                     │
│  quality_review.py ──→ quality_report.json                          │
│  (Gemini 2.5 Pro + GPT-4o dual review, auto-fix)                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  Phase 4 — Output                                                   │
│                                                                     │
│  convert_to_html.py ──→ html_output/*.html (styled career pages)    │
│  career_graph_interactive.py ──→ career_graph.html (network viz)    │
│  career_graph.py ──→ career_graph.png (static image)                │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
├── Data Management/
│   ├── load_data.py               # Initial data source exploration
│   ├── prepare_data.py            # Pull from O*NET + BLS, deduplicate
│   ├── trim_data.py               # Rank by salary keywords, trim to 3,300
│   ├── occupation_data.json       # Raw combined dataset
│   └── final_data.json            # Production dataset (3,300 careers)
│
├── Final Wiki Pages/
│   ├── pipeline.py                # Main generation pipeline (skip-if-exists)
│   ├── update_pipeline.py         # Force-overwrite pipeline
│   ├── quality_review.py          # Dual-model QA with auto-fix
│   ├── view_report.py             # Print quality report summary
│   ├── convert_to_html.py         # Markdown → styled HTML pages
│   ├── career_graph.py            # Static PNG network graph
│   ├── career_graph_interactive.py # Interactive HTML network graph
│   ├── test_connections.py        # Verify API + storage connections
│   └── html_output/               # Generated HTML career pages
│
├── logo.jpg                       # Branding asset
├── .env                           # API keys (not committed)
└── README.md
```

## Setup

### Prerequisites

- Python 3.10+
- Azure Storage account with a blob container
- Gemini API key (Google AI Studio)
- Azure OpenAI deployment (for quality review)

### Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_key
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_CONTAINER_NAME=your_container
AZURE_OPENAI_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
```

### Install Dependencies

```bash
pip install google-genai openai azure-storage-blob python-dotenv requests markdown networkx matplotlib
```

### Verify Connections

```bash
python test_connections.py
```

## Usage

### 1. Prepare the Dataset

Pull occupation data from O\*NET and BLS, deduplicate, and trim to the top 3,300 careers ranked by salary relevance:

```bash
cd "Data Management"
python prepare_data.py
python trim_data.py
```

This produces `final_data.json` — the input for all downstream steps.

### 2. Generate Wiki Pages

Run the main pipeline. It enriches each career with structured data via the Gemini API, then generates a 2,000–3,000 word wiki page and uploads it to Azure Blob Storage. The pipeline checkpoints automatically — if it stops, re-running skips careers that already have a blob.

```bash
cd "Final Wiki Pages"
python pipeline.py
```

To force-regenerate existing pages (e.g., after prompt changes):

```bash
python update_pipeline.py                          # Regenerate all
python update_pipeline.py --batch 100              # First 100 only
python update_pipeline.py --only-existing           # Only overwrite existing pages
python update_pipeline.py --ids career-29-1141-00   # Specific career IDs
```

### 3. Run Quality Review

Dual-model review using both Gemini 2.5 Pro and GPT-4o. Each page is checked for factual errors, tone issues, missing sections, and word count. Pages with issues are automatically fixed and re-uploaded.

```bash
python quality_review.py
python view_report.py    # Print summary
```

### 4. Generate Outputs

**Styled HTML pages** — converts every markdown page in Azure to a branded, responsive HTML page:

```bash
python convert_to_html.py
# Output: html_output/*.html
```

**Interactive career graph** — builds a force-directed network visualization showing how careers relate to each other. Opens in any browser with zoom, pan, hover, click-to-explore, search, and legend filtering:

```bash
python career_graph_interactive.py
# Output: career_graph.html
```

**Static graph image** — PNG export for presentations or print:

```bash
python career_graph.py --nodes 500
# Output: career_graph.png
```

## Pipeline Details

### Content Generation

Each career goes through a two-step process:

1. **Enrichment** — Gemini receives the career title and O\*NET description, returns structured JSON with salary ranges, top industries, skills, education pathways, career trajectories, interview prep, and more.

2. **Wiki writing** — Gemini receives the enrichment data and writes a polished markdown article with standardized sections: Overview, Day in the Life, Essential Skills, Education Pathways, Salary & Compensation, Industry Outlook, Interview Prep, 30/60/90 Day Plan, Pros & Cons, and Related Careers.

The pipeline includes exponential backoff retry logic for rate limits and transient API errors.

### Quality Review

The review pipeline pulls pages from Azure and runs each through two independent AI reviewers:

- **Gemini 2.5 Pro** — checks for factual errors, tone issues, unrealistic statistics
- **GPT-4o** — second opinion on the same criteria

Results are merged (deduplicated by issue type), and any page with issues is automatically fixed by Gemini and re-uploaded. A JSON report is saved locally.

### Career Graph

The interactive graph represents career relationships using four connection layers:

- **Minor group mesh** — careers in the same O\*NET detailed group are fully interconnected
- **Major group links** — each career connects to 4–6 peers in its broader family
- **Inter-group bridges** — 30+ cross-cluster relationships between related fields
- **Hub spokes** — central node connects to every career for the radial layout

Node colors represent 23 career families (Management, Healthcare, Tech, etc.). The layout is pre-computed using networkx's spring algorithm with 300 iterations, then baked into the HTML — no live physics, just smooth zoom/pan interaction.

## Data Sources

- [O\*NET 29.0](https://www.onetcenter.org/database.html) — 1,016 base occupations + alternate titles
- [BLS Occupational Outlook Handbook](https://www.bls.gov/ooh/) — supplementary career categories

## License

This project is for educational purposes. O\*NET data is public domain (U.S. Department of Labor). BLS data is public domain.

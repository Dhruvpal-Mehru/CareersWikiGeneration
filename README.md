# Career Wiki Content Pipeline

Production-grade agentic content pipeline using multi-stage LLM orchestration to generate comprehensive career intelligence pages at scale. Combines Google Gemini and Azure OpenAI for generation and quality assurance, with Azure Blob Storage for cloud delivery. Includes resilience patterns, rate limit handling, and pluggable LLM provider architecture.

---

## What This Does

This pipeline takes a list of US career titles from O*NET and produces 2,000–3,000 word educational wiki pages for each one — covering salary ranges, day in the life, interview prep, 30/60/90 day plans, and more. Pages are stored as markdown in Azure Blob Storage and can be converted to HTML for viewing.

---

## Tech Stack

| Component | Service |
|---|---|
| LLM (generation) | Google Gemini 2.5 Flash (free tier) |
| LLM (quality review) | Gemini 2.5 Flash + Azure OpenAI GPT-4o |
| Storage | Azure Blob Storage |
| Language | Python 3.14 |
| Environment | PyCharm / venv |

---

## Project Structure

```
project-root/
├── .env.example                  # Template for new developers
├── .gitignore
├── .venv/                        # Python virtual environment
│
├── Connection Check/
│   └── test_connections.py       # Verify all API connections work
│
├── Data Management/
│   ├── final_data.json           # 4,000 prepared career entries (ready to use)
│   ├── occupation_data.json      # Raw O*NET career data
│   ├── prepare_data.py           # Download O*NET data from source
│   ├── trim_data.py              # Filter + prioritize 4,000 high-salary careers
│   └── load_data.py              # Data source utilities
│
├── Wiki Production/
│   └── pipeline.py               # Main generation pipeline
│
├── Quality Assurance/
│   ├── quality_review.py         # Dual-model review + auto-fix
│   ├── view_report.py            # Print quality report summary
│   └── quality_report_*.json     # Generated reports (auto-saved after each run)
│
└── Final Wiki Pages/
    ├── convert_to_html.py        # Convert Azure markdown → local HTML pages
    ├── logo.jpg                  # Logo (embedded in HTML output)
    └── html_output/              # Generated HTML pages (open in browser)
```

---

## Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd project-root
python -m venv .venv

# Activate (Mac/Linux)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install openai azure-storage-blob python-dotenv requests google-genai markdown
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```bash
# Google Gemini (free tier — get key at aistudio.google.com)
GEMINI_API_KEY=your_gemini_key_here

# Azure OpenAI
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_CONTAINER_NAME=your_container_name
```

### 4. Create Azure resources

You will need:
- An Azure OpenAI resource with a GPT-4o deployment
- An Azure Storage account with a blob container

Add their credentials to `.env` as shown above.

### 5. Verify all connections

```bash
python "Connection Check/test_connections.py"
```

Expected output:
```
Testing Gemini...
✅ Gemini works: Hello! ...
Testing Azure OpenAI...
✅ OpenAI works: Hello! ...
Testing Azure Blob Storage...
✅ Blob Storage works: test file uploaded!
🚀 All connections working — ready to build!
```

---

## Running the Pipeline

### Step 1 — Prepare career data (skip if final_data.json already exists)

```bash
python "Data Management/prepare_data.py"
python "Data Management/trim_data.py"
```

### Step 2 — Generate wiki pages

```bash
python "Wiki Production/pipeline.py"
```

This will:
- Load all careers from `Data Management/final_data.json`
- Generate enriched 2,000–3,000 word markdown for each
- Upload to Azure Blob Storage under `careers/`
- Skip pages already generated (checkpoint system)
- Resume automatically if stopped

Expected output:
```
📂 Loaded 4000 careers
🚀 Starting pipeline — safe to leave running overnight!

[1/4000] Chief Executives
⚙️  Enriching: Chief Executives
📝 Writing wiki: Chief Executives
✅ Uploaded: careers/career-11-1011-00.md

📊 Progress: 50 done, 0 skipped, 0 failed
```

### Step 3 — Quality review

```bash
python "Quality Assurance/quality_review.py"
```

Runs every page through both Gemini and GPT-4o checking for:
- Missing required sections
- Factual errors or unrealistic statistics
- Unprofessional or off-tone writing

Automatically fixes issues and re-uploads to Azure. Saves a JSON report on completion.

To review a subset only (e.g. first 50 for demo), edit `quality_review.py`:
```python
blobs = list(container.list_blobs(name_starts_with="careers/"))[:50]
```

View the report after it completes:
```bash
python "Quality Assurance/view_report.py"
```

### Step 4 — Convert to HTML

```bash
python "Final Wiki Pages/convert_to_html.py"
```

Downloads all markdown from Azure and converts each to a styled HTML page saved in `Final Wiki Pages/html_output/`. Open any `.html` file in your browser to view.

---

## Pipeline Architecture

```
O*NET career data (Data Management/final_data.json)
              ↓
Stage 1: Context enrichment (Gemini)
              ↓ salary, skills, companies, city data
Stage 2+3: Content generation (Gemini)
              ↓ 2,000–3,000 word markdown
Stage 4: Quality review (Gemini + GPT-4o)
              ↓ auto-fix if issues found
Stage 5: Azure Blob Storage (careers/ folder)
              ↓
HTML converter → Final Wiki Pages/html_output/
```

---

## Content Structure

Every generated wiki page includes:

- Frontmatter (title, type, description)
- Overview
- A Day in the Life
- Core Knowledge Areas
- Essential Skills (technical, soft, tools)
- Education and Training Pathways
- Career Trajectories and Opportunities
- Salary and Compensation (entry/mid/senior + by city)
- Industry Outlook and Future Trends
- Interview Prep and Getting Hired
- Getting Started — 30/60/90 Day Plan
- Pros and Cons
- Related Careers

---

## Swapping LLM Providers

The pipeline is provider-agnostic. All config lives in `.env` — swap providers by changing keys and updating the model name in `pipeline.py`:

```python
# Current: Gemini 2.5 Flash (free)
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"

# To switch to Azure OpenAI GPT-4o:
# Replace gemini.models.generate_content() calls
# with openai_client.chat.completions.create()
```

---

## Rate Limits and Cost

| Service | Limit | Cost |
|---|---|---|
| Gemini 2.5 Flash | 10,000 requests/day | Free |
| Azure OpenAI GPT-4o | 300 RPM | Pay per token |
| Azure Blob Storage | 5GB / 50K ops free | Free tier |

For 4,000 pages at 2 calls each = 8,000 calls — fits within one day of Gemini free quota.

---

## Known Limitations

- Fields of study (CIP codes) not yet generated — careers only
- No Azure CDN configured — pages served directly from blob storage
- No Azure SQL progress tracking — uses blob existence check as checkpoint instead
- Docker containerization not implemented
- ~1–3% of pages may fail during enrichment due to JSON parsing errors — re-running the pipeline retries these automatically

---

## License

MIT

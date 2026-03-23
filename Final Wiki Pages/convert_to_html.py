import os
import base64
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import markdown

load_dotenv()

blob_service = BlobServiceClient.from_connection_string(
    os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)
container = blob_service.get_container_client(
    os.getenv("AZURE_CONTAINER_NAME")
)

os.makedirs("html_output", exist_ok=True)

# Embed logo as base64
with open("logo.jpg", "rb") as f:
    LOGO_B64 = base64.b64encode(f.read()).decode("utf-8")
LOGO_TAG = f'<img src="data:image/jpeg;base64,{LOGO_B64}" style="height:36px;width:auto;" alt="MascotGO">'

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — MascotGO Career Guide</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #fafaf8;
            color: #1c1917;
            line-height: 1.7;
        }}
        .accent-bar {{
            height: 5px;
            background: linear-gradient(90deg, #f59e0b 0%, #ef4444 50%, #8b5cf6 100%);
        }}
        .nav {{
            background: #fafaf8;
            border-bottom: 1px solid #e7e5e4;
            padding: 14px 60px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .nav-tag {{
            font-size: 11px;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #a8a29e;
            font-weight: 500;
        }}
        .hero {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 64px 60px 48px;
            border-bottom: 1px solid #e7e5e4;
        }}
        .eyebrow {{
            font-size: 11px;
            letter-spacing: 2.5px;
            text-transform: uppercase;
            color: #f59e0b;
            font-weight: 700;
            margin-bottom: 18px;
        }}
        .hero h1 {{
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 3em;
            font-weight: 700;
            color: #1c1917;
            line-height: 1.15;
            letter-spacing: -1px;
            margin-bottom: 18px;
        }}
        .deck {{
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 1.2em;
            color: #57534e;
            line-height: 1.65;
            font-style: italic;
            max-width: 780px;
            margin-bottom: 32px;
        }}
        .meta-row {{
            display: flex;
            gap: 48px;
            padding-top: 24px;
            border-top: 1px solid #e7e5e4;
            flex-wrap: wrap;
        }}
        .meta-item label {{
            font-size: 10px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: #a8a29e;
            font-weight: 600;
            display: block;
            margin-bottom: 4px;
        }}
        .meta-item span {{
            font-size: 15px;
            font-weight: 700;
            color: #1c1917;
        }}
        .content-wrap {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 56px 60px;
            display: grid;
            grid-template-columns: 1fr 220px;
            gap: 72px;
            align-items: start;
        }}
        .article h2 {{
            font-family: Georgia, serif;
            font-size: 1.5em;
            font-weight: 700;
            color: #1c1917;
            margin: 48px 0 16px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f59e0b;
        }}
        .article h2:first-child {{ margin-top: 0; }}
        .article h3 {{
            font-weight: 700;
            color: #292524;
            margin: 28px 0 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.85em;
        }}
        .article p {{
            font-size: 1.05em;
            color: #44403c;
            margin-bottom: 18px;
            line-height: 1.8;
        }}
        .article ul, .article ol {{
            margin: 12px 0 20px 20px;
        }}
        .article li {{
            font-size: 1.02em;
            color: #44403c;
            margin-bottom: 8px;
            line-height: 1.7;
        }}
        .article strong {{ color: #1c1917; font-weight: 700; }}
        .article blockquote {{
            border-left: 3px solid #f59e0b;
            padding: 12px 20px;
            margin: 24px 0;
            background: #fffbeb;
            border-radius: 0 8px 8px 0;
        }}
        .article blockquote p {{ color: #78716c; font-style: italic; margin: 0; }}
        .article hr {{ border: none; border-top: 1px solid #e7e5e4; margin: 40px 0; }}
        .article code {{
            background: #f5f5f4;
            padding: 2px 7px;
            border-radius: 4px;
            font-size: 0.88em;
            color: #ef4444;
        }}
        .sidebar {{ position: sticky; top: 32px; }}
        .sidebar-card {{
            background: white;
            border: 1px solid #e7e5e4;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .sidebar-card h4 {{
            font-size: 10px;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #a8a29e;
            font-weight: 700;
            margin-bottom: 14px;
        }}
        .sidebar-stat {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #f5f5f4;
        }}
        .sidebar-stat:last-child {{ border-bottom: none; padding-bottom: 0; }}
        .sidebar-stat .ss-label {{ font-size: 11px; color: #78716c; }}
        .sidebar-stat .ss-val {{ font-size: 12px; font-weight: 700; color: #1c1917; }}
        .tag-cloud {{ display: flex; flex-wrap: wrap; gap: 5px; }}
        .tag {{
            background: #fafaf8;
            border: 1px solid #e7e5e4;
            padding: 3px 8px;
            border-radius: 20px;
            font-size: 10px;
            color: #57534e;
        }}
        .mascotgo-badge {{
            background: linear-gradient(135deg, #1c1917, #292524);
            color: white;
            border-radius: 12px;
            padding: 18px;
            text-align: center;
        }}
        .mascotgo-badge p {{
            font-size: 11px;
            color: #a8a29e;
            line-height: 1.5;
            margin-top: 8px;
        }}
        .footer {{
            border-top: 1px solid #e7e5e4;
            padding: 32px 60px;
            text-align: center;
        }}
        .footer-inner {{ max-width: 1200px; margin: 0 auto; }}
        .footer p {{ font-size: 12px; color: #a8a29e; margin-top: 6px; }}
        @media (max-width: 900px) {{
            .content-wrap {{ grid-template-columns: 1fr; gap: 40px; }}
            .sidebar {{ position: static; }}
            .hero h1 {{ font-size: 2em; }}
            .meta-row {{ gap: 20px; }}
            .nav, .hero, .content-wrap, .footer {{ padding-left: 24px; padding-right: 24px; }}
        }}
    </style>
</head>
<body>

<div class="accent-bar"></div>

<nav class="nav">
    {logo}
    <div class="nav-tag">Career Intelligence</div>
</nav>

<div class="hero">
    <div class="eyebrow">Career Guide</div>
    <h1>{title}</h1>
    <p class="deck">{description}</p>
    <div class="meta-row">
        <div class="meta-item">
            <label>Market</label>
            <span>United States</span>
        </div>
        <div class="meta-item">
            <label>Content</label>
            <span>2,000+ words</span>
        </div>
        <div class="meta-item">
            <label>Updated</label>
            <span>2026</span>
        </div>
    </div>
</div>

<div class="content-wrap">
    <article class="article">
        {content}
    </article>
    <aside class="sidebar">
        <div class="sidebar-card">
            <h4>Quick facts</h4>
            <div class="sidebar-stat">
                <span class="ss-label">Market</span>
                <span class="ss-val">United States</span>
            </div>
            <div class="sidebar-stat">
                <span class="ss-label">Content type</span>
                <span class="ss-val">Career wiki</span>
            </div>
            <div class="sidebar-stat">
                <span class="ss-label">Reading time</span>
                <span class="ss-val">~10 min</span>
            </div>
            <div class="sidebar-stat">
                <span class="ss-label">Last updated</span>
                <span class="ss-val">2026</span>
            </div>
        </div>
        <div class="sidebar-card">
            <h4>Topics covered</h4>
            <div class="tag-cloud">
                <span class="tag">Salary ranges</span>
                <span class="tag">Day in the life</span>
                <span class="tag">Education paths</span>
                <span class="tag">Interview prep</span>
                <span class="tag">30/60/90 plan</span>
                <span class="tag">Job outlook</span>
                <span class="tag">Related careers</span>
            </div>
        </div>
        <div class="mascotgo-badge">
            {logo}
            <p>Career intelligence platform helping students find their path</p>
        </div>
    </aside>
</div>

<footer class="footer">
    <div class="footer-inner">
        {logo}
        <p>Career Intelligence Platform — Empowering students to find their path</p>
    </div>
</footer>

</body>
</html>"""


def convert_md_to_html(blob_name):
    blob_client = container.get_blob_client(blob_name)
    md_content = blob_client.download_blob().readall().decode("utf-8")

    title = "Career Guide"
    description = ""
    if md_content.startswith("---"):
        parts = md_content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            md_content = parts[2].strip()
            for line in frontmatter.split("\n"):
                if line.startswith("title:"):
                    title = line.replace("title:", "").strip().strip('"')
                if line.startswith("description:"):
                    description = line.replace("description:", "").strip().strip('"')

    html_content = markdown.markdown(
        md_content,
        extensions=["extra", "toc"]
    )

    full_html = HTML_TEMPLATE.format(
        title=title,
        description=description,
        content=html_content,
        logo=LOGO_TAG
    )

    safe_name = blob_name.replace("careers/", "").replace(".md", ".html")
    output_path = f"html_output/{safe_name}"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    return output_path


def convert_all():
    print("📥 Fetching pages from Azure...")
    blobs = list(container.list_blobs(name_starts_with="careers/"))
    total = len(blobs)
    print(f"Found {total} career pages\n")

    for i, blob in enumerate(blobs):
        try:
            path = convert_md_to_html(blob.name)
            print(f"[{i+1}/{total}] ✅ {blob.name}")
        except Exception as e:
            print(f"[{i+1}/{total}] ❌ {blob.name} — {e}")

    print(f"\n🎉 Done! Open html_output/ folder to view your pages")


if __name__ == "__main__":
    convert_all()
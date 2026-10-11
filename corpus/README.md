# corpus/

Put the official PDFs here (they are gitignored, so only this README and `sources.csv` are committed).

## Rules for adding a document
1. Download it from an **official** source (ministry or department site, scholarships.gov.in, pmkisan.gov.in, a state portal).
2. Check it's **text-based**: open it and try selecting text. Skip scanned images for now.
3. Give it a short, clean filename: `pm-kisan-operational-guidelines.pdf`.
4. Add a row to `sources.csv`. The `title` and `source_url` are shown to users in citations.

## Suggested scope (about 40–80 docs)
- Central scholarships (pre-/post-matric, merit-cum-means, top-class education; NSP guidelines)
- 5–10 major central schemes: PM-KISAN, PMAY, Ayushman Bharat PM-JAY, PM Ujjwala, Sukanya Samriddhi, PM SVANidhi, Stand-Up India
- Gujarat state schemes for students and farmers (e.g. scholarship and agriculture-department scheme guidelines)
- Hindi versions of 5–10 of the above, if available (for the multilingual demo)

## Ingest
```powershell
cd apps/api
uv run python -m scripts.ingest_folder ../../corpus
```

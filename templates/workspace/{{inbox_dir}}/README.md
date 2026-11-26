# {{dir_inbox_dir}} — where fetched PDFs land

**Agents never download.** Scouts list candidates; {{owner}} fetches. A PDF is a candidate until it
is read, DOI-confirmed and curated.

Drop convention: `{{dir_inbox_dir}}/wave<N>/<citekey>.pdf`, the citekey **exactly** as it appears in
`FETCH_LIST.md`. A misnamed drop is the likeliest human error in the pipeline; `survey verify` §12
catches it, but only after the fact. Put anything fetched but not on the list in `wave<N>/_unlisted/`.

After a wave lands, run the `survey-ingest` skill: it checks every file really is a PDF (a 324-byte
HTML 404 saved as `.pdf` once fooled a whole workspace), classifies transcriptions, indexes the new
rows, and re-runs GATE 1.

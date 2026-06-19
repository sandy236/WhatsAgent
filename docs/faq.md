# FAQ

## Where are the docs published?

The GitHub Actions workflow deploys the MkDocs site to GitHub Pages using the `gh-pages` branch.

## How do I rebuild docs locally?

Install the docs dependencies and run:

```bash
python -m pip install -r requirements-docs.txt
mkdocs serve
```

## What folder contains the source docs?

Source files live in the `docs/` directory and the site configuration is at `mkdocs.yml`.

## How do I keep WhatsApp traffic secure?

For production, add a shared secret or API key between `wa-gateway` and the backend, and do not expose the gateway directly without TLS.

## Which Python version should I use?

Use Python 3.12 or 3.13 for backend compatibility and to avoid native build issues on Windows.

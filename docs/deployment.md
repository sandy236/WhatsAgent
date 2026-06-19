# Deployment

## GitHub Pages docs

This repository includes a GitHub Actions workflow to publish MkDocs documentation to GitHub Pages.

### Build locally

```bash
python -m pip install -r requirements-docs.txt
mkdocs serve
```

Open the local preview at `http://127.0.0.1:8000`.

### GitHub Action

The workflow deploys documentation to the `gh-pages` branch automatically when changes are pushed to `main` or `master`.

## Production deployment

The main application can run in Docker Compose or using the local backend/frontend/gateway setup.

### Docker Compose

```bash
docker compose up -d --build
```

### Environment

Copy `.env.example` to `.env` and configure environment variables before starting the stack.

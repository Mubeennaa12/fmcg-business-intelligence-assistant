# FMCG Beverages Business Intelligence Assistant - Hugging Face Deployment Plan

This document details the deployment strategy on **Hugging Face Spaces** using a single Docker container.

## Hugging Face Spaces Architecture

```mermaid
graph TD
    User([User]) <--> SpacesPort[HF Spaces Port 7860]
    
    subgraph HF Spaces Single Docker Container
        SpacesPort <--> FastAPI[FastAPI Server]
        FastAPI <--> API[/api Endpoints]
        FastAPI <--> StaticFiles[Static Frontend Files /out]
        FastAPI <--> DB[(SQLite Database)]
    end
```

### 1. Unified Single-Container Execution
Hugging Face Spaces exposes only a single container on a single port (usually `7860`). To run our full-stack application:
- **Next.js Static Export**: We configure Next.js to generate static HTML/JS/CSS assets (`output: 'export'`).
- **FastAPI Static Hosting**: We copy the built Next.js static assets into a `/static` directory in our FastAPI backend and mount it at the root `/` path. This eliminates the need for separate frontend/backend processes and Nginx reverse proxies.
- **Relative API Calls**: We update `api.ts` to use relative paths (`/api`) instead of `http://localhost:8000/api`. The frontend will automatically target the Hugging Face Spaces domain hosting the server.

### 2. Multi-Stage Dockerfile
We will create a root-level `Dockerfile` that:
1. **Build Stage (Node)**: Installs npm packages in `/frontend` and builds the static site into `frontend/out`.
2. **Runtime Stage (Python)**: Installs Python requirements, copies the backend code, copies the compiled Next.js files from the Build Stage into the backend's static directory, and launches FastAPI via Uvicorn on port `7860`.

### 3. Hugging Face Spaces Metadata
We will prefix `README.md` with Hugging Face Space YAML metadata so HF automatically detects the Docker configuration:
```yaml
---
title: FMCG Beverages BI Assistant
emoji: 🍹
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---
```

---

## Proposed Changes

### Root Folder

#### [NEW] [Dockerfile](file:///D:/business%20Intelligent%20assistant/Dockerfile)
A unified multi-stage Dockerfile containing:
- Node.js build stage (compiles frontend)
- Python runtime stage (serves FastAPI + static assets on port 7860)

#### [MODIFY] [README.md](file:///D:/business%20Intelligent%20assistant/README.md)
- Add Hugging Face Space metadata block at the top.
- Add deployment instructions.

### Frontend Component (`/frontend`)

#### [MODIFY] [next.config.ts](file:///D:/business%20Intelligent%20assistant/frontend/next.config.ts)
- Configure `output: 'export'` and disable image optimization (required for static exports).

#### [MODIFY] [src/app/api.ts](file:///D:/business%20Intelligent%20assistant/frontend/src/app/api.ts)
- Make `API_BASE_URL` dynamic: `/api` or window location origin.

### Backend Component (`/backend`)

#### [MODIFY] [app/main.py](file:///D:/business%20Intelligent%20assistant/backend/app/main.py)
- Import `StaticFiles`.
- Mount `StaticFiles` at `/` after all other `/api` endpoints have been registered.

---

## Verification Plan

1. Build the unified Docker image locally:
   ```bash
   docker build -t fmcg-assistant .
   ```
2. Run the container locally mapping port 7860:
   ```bash
   docker run -p 7860:7860 fmcg-assistant
   ```
3. Open `http://localhost:7860` in the browser and verify:
   - Dashboard page loads correctly (verifying static file routing).
   - KPI values and charts render (verifying backend API integration).
   - Conversational chat works.

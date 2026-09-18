# Campaign Comparator — frontend

React (Vite) app. Talks to the FastAPI backend (`api.py`, one level up) over HTTP —
run that first.

## Setup
```
cd app
npm install
```

## Run (development)
```
npm run dev
```
Opens on http://localhost:5173 — make sure `api.py` is running on port 8000 first
(`uvicorn api:app --reload --port 8000` from the project root).

## Build for production
```
npm run build
```
Outputs static files to `app/dist/` — serve that folder with any static file server.

## Config
The API URL defaults to `http://localhost:8000`. To point at a different backend, create
`app/.env` with:
```
VITE_API_URL=http://your-backend-host:8000
```

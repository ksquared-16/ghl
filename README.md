# Alloy

Alloy is a marketplace connecting homeowners with trusted local service professionals, starting with home cleaning in Bend, Oregon.

This repository contains:
- **backend/** – Python-based dispatcher/API that integrates with GoHighLevel (GHL) and Twilio for SMS flows
- **web/** – Next.js marketing website and lead generation frontend

## Repository Structure

```
.
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI dispatcher application
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment variable template
├── web/
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # React components
│   ├── lib/                 # Utility functions and API helpers
│   ├── public/              # Static assets
│   └── ...
└── README.md
```

## Backend Setup

The backend is a FastAPI application that handles:
- Job dispatch to contractors via GHL and SMS
- Contractor reply processing
- Lead submission from the frontend website
- Pros application submissions

### Prerequisites

- Python 3.8+
- Virtual environment (venv)

### Installation

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment:
   ```bash
   # On macOS/Linux:
   source .venv/bin/activate
   
   # On Windows:
   .venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file (copy from `.env.example` if available, or create manually):
   ```bash
   # Required environment variables:
   GHL_API_KEY=your_ghl_api_key_here
   GHL_LOCATION_ID=your_ghl_location_id_here
   ```

### Running the Backend

Start the development server:

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`

- API docs: `http://localhost:8000/docs` (Swagger UI)
- Health check: `http://localhost:8000/`

### Backend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GHL_API_KEY` | GoHighLevel API Bearer token | Yes |
| `GHL_LOCATION_ID` | GoHighLevel location ID | Yes |

## Frontend Setup

The frontend is a Next.js 14+ application with TypeScript and Tailwind CSS.

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Navigate to the web directory:
   ```bash
   cd web
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env.local` file:
   ```bash
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```

### Running the Frontend

Start the development server:

```bash
npm run dev
```

The website will be available at `http://localhost:3000`

### Frontend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_BASE_URL` | Base URL of the backend API (e.g., `http://localhost:8000` in dev) | Yes |

## Development Workflow

1. **Start the backend** (in one terminal):
   ```bash
   cd backend
   source .venv/bin/activate  # or activate on Windows
   uvicorn backend.main:app --reload
   ```

2. **Start the frontend** (in another terminal):
   ```bash
   cd web
   npm run dev
   ```

3. The frontend at `http://localhost:3000` will communicate with the backend at `http://localhost:8000`

## API Endpoints

### Public Endpoints

- `GET /` – Health check
- `GET /contractors` – List eligible contractors
- `POST /leads/cleaning` – Submit a cleaning lead from the website
- `POST /leads/pros` – Submit a pros application

### Webhook Endpoints (called by GHL)

- `POST /dispatch` – Called when a customer books an appointment
- `POST /contractor-reply` – Called when a contractor replies to a dispatch SMS

### Debug Endpoints

- `GET /debug/jobs` – View in-memory job cache (development only)

## Future Work

- Split dispatcher functions into separate modules for better organization
- Add more service verticals (beyond home cleaning)
- Add database persistence for jobs (currently in-memory)
- Add authentication/authorization for admin endpoints
- Expand API documentation with more examples
- Add integration tests

## Brand Guidelines

The frontend uses the following brand colors (defined in Tailwind config):

- **Alloy Blue** (`#00458C`) – Primary brand color
- **Bend Pine** (`#273F52`) – Muted green/blue accent
- **Juniper** (`#00A283`) – Calm, fresh accent
- **Ember** (`#BC4300`) – Warm accent (use sparingly)
- **River Stone** (`#F4F6F9`) – Light neutral background
- **Midnight Forge** (`#18273A`) – Dark text/background

Typography: **Poppins** (all weights) via Google Fonts

Brand values: Trust First, Fair for Everyone, Human + Smart, Dead-Simple, Local Proud


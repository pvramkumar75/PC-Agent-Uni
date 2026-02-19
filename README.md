# OmniMind — Universal AI Personal Assistant

A **powerful, private** AI assistant that lives on your computer. Host the UI on Vercel and control your PC from anywhere, or run everything locally. 

## 🚀 Two Ways to Run

### Option 1: The Modern Way (Vercel + Local Engine)
1. **Deploy to Vercel**: Push this repo to GitHub and connect it to Vercel.
2. **Launch Engine**: Run `python run_local.py` on your PC.
3. **Connect**: Open your Vercel link, go to **Settings**, and ensure the URL matches your local engine.

### Option 2: Full Local (Docker)
```bash
# 1. Configure
cp .env.example .env   # Add your DEEPSEEK_API_KEY

# 2. Run
docker-compose up --build

# 3. Open
http://localhost:3000
```

## 🧠 Universal Capabilities
- 🔍 **Universal Search**: Now drive-agnostic! Finds "Desktop", "Downloads", or any file across all available drives (C:, D:, etc.) automatically.
- 🤯 **Vercel-Ready**: Shared link support. Anyone with the link can use it on their own PC by running the local engine.
- 🧠 **Document Intelligence**: Deep analysis of PDF, Excel, Word, and Images (OCR).
- 📁 **Cloud-Private**: Your files NEVER leave your PC. The Vercel UI connects directly to your localhost.

## 🧠 Capabilities

| Feature | Description |
|---------|-------------|
| **Chat** | Natural language queries with Markdown-formatted responses |
| **File Search** | Find files anywhere on D: drive or user folders |
| **Document Analysis** | Extract data from PDF, Excel, Word, CSV, images (OCR) |
| **Folder Organization** | Sort files by type, move/copy/rename with AI commands |
| **Quote Comparison** | Multi-vendor tables with price/delivery analysis |
| **Email Drafting** | Negotiation and follow-up emails (requires approval) |
| **Persistent Memory** | SQLite + ChromaDB for vendor history and price trends |

## 📁 Project Structure

```
Purchase Agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints (chat, upload, organize)
│   │   ├── core/
│   │   │   ├── config.py        # Settings & environment variables
│   │   │   ├── llm.py           # DeepSeek API wrapper (chat + reasoner)
│   │   │   └── memory.py        # SQLite + ChromaDB memory engine
│   │   ├── agents/
│   │   │   └── procurement_agent.py  # Document processing pipeline
│   │   ├── tools/
│   │   │   ├── computer_search.py    # Full disk search & organization
│   │   │   ├── file_processor.py     # PDF/Excel/Word/Image reader
│   │   │   ├── comparison_engine.py  # Vendor quote comparison
│   │   │   ├── email_service.py      # Gmail SMTP integration
│   │   │   └── ocr.py               # Tesseract OCR
│   │   └── watcher/
│   │       └── folder_watcher.py     # Auto-process new files
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Chat UI with Markdown rendering
│   │   ├── main.jsx             # React entry point
│   │   └── index.css            # Tailwind + Inter font
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env
└── workspace/                   # Auto-created workspace folders
    ├── inbox/
    ├── rfq/
    ├── orders/
    ├── archive/
    ├── output/
    └── memory/
```

## 🔒 Security

- **Local-first**: All processing runs on your machine. Only DeepSeek API calls go external.
- **No deletions**: The AI can only move/copy files, never delete.
- **Human-in-the-loop**: Emails require explicit approval before sending.
- **Drive access**: D: and C:/Users are mounted read-write inside the container.

## 🛠 Tech Stack

- **Backend**: FastAPI, Python 3.11, DeepSeek API
- **Frontend**: React 18, Vite, Tailwind CSS, Framer Motion
- **Memory**: SQLite (structured) + ChromaDB (vector/semantic)
- **OCR**: Tesseract via pytesseract
- **Containerization**: Docker Compose

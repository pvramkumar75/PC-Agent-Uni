from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import json
import logging
import asyncio
import re
import time

from app.core.config import settings
from app.core.memory import memory_manager
from app.core.llm import llm_engine
from app.agents.procurement_agent import procurement_agent
from app.tools.email_service import email_service
from app.tools.computer_search import computer_tools
from app.watcher.folder_watcher import start_watcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Ensure all workspace directories exist ──────────────────────────
WORKSPACE_DIRS = [
    settings.RFQ_DIR, settings.INBOX_DIR, settings.ORDERS_DIR,
    settings.ARCHIVE_DIR, settings.OUTPUT_DIR, settings.MEMORY_DIR,
]
for d in WORKSPACE_DIRS:
    os.makedirs(d, exist_ok=True)

# ─── App ─────────────────────────────────────────────────────────────
app = FastAPI(title="OmniMind — Universal AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Startup ─────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("Starting folder watcher...")
    asyncio.create_task(start_watcher())

# ─── Health ──────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "online", "agent": "OmniMind", "version": "3.0"}

# ─── Upload ──────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and immediately analyze a document."""
    upload_dir = settings.INBOX_DIR
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    logger.info(f"File uploaded: {file_path}")
    
    try:
        result = await procurement_agent.process_new_document(file_path)
        return {"status": "success", "file": file.filename, "analysis": result}
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return {"status": "uploaded", "file": file.filename, "analysis": {"summary": f"File saved. Analysis error: {str(e)}"}}

# ─── Knowledge ───────────────────────────────────────────────────────
@app.get("/knowledge")
async def get_knowledge():
    """Fetch learned patterns and facts."""
    facts = memory_manager.get_learned_facts(limit=15)
    return {"facts": facts}

@app.post("/open")
async def open_file(body: Dict[str, str]):
    """Open a file or folder on the local computer."""
    path = body.get("path")
    if not path:
        return {"status": "error", "message": "No path provided"}
    
    # 1. Clean path
    path = path.strip().replace('"', '').replace("'", "")
    
    # 2. Try several normalization variants
    variants = [
        path,
        path.replace("/", "\\"),
        path.replace("\\", "/"),
        path.replace("/host_d/", "D:\\").replace("/", "\\"),
        path.replace("/host_users/", "C:\\Users\\").replace("/", "\\"),
        path.replace("D:/", "D:\\"),
        path.replace("C:/", "C:\\"),
    ]
    
    for v in variants:
        try:
            if os.path.exists(v):
                os.startfile(v)
                return {"status": "success", "message": f"Opened {v}"}
        except:
            continue
            
    return {"status": "error", "message": f"Path not found or could not be opened: {path}"}

# ─── CHAT — The Versatile Brain ──────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, str]] = []

SYSTEM_PROMPT = """You are **OmniMind**, a powerful, highly-versatile autonomous AI assistant with full, deep access to the user's computer.

## YOUR IDENTITY
- You are a **proactive operations assistant** designed to make the user's life effortless.
- You perform complex tasks like searching, reading, analyzing, and organizing files across the entire computer.
- You are exceptionally good at procurement, but your intelligence extends to general business, personal organization, and data analysis.
- You think step-by-step, use your tools with precision, and always provide clear, structured results.

## COMPUTER ACCESS
You have direct line-of-sight to the following:
- `/host_d/` → Full D: drive access (main storage)
- `/host_users/` → C:/Users (Desktop, Downloads, Documents)
- `/host_capex/` → \\tplserver\Materials (Production & Network data)
- `/workspace/` → Internal project workspace for processing & memory

## CAPABILITIES
1. **🔍 Full-Disk Search** — Find any file or folder by name, extension, or context.
2. **🧠 Document Intelligence** — Extract, summarize, and analyze data from PDF, Excel, Word, CSV, and even images (OCR).
3. **📁 Autonomous Organization** — Proactively suggest and execute file moves, copies, and folder cleanups (sort by type, project, or date).
4. **📊 Specialized Procurement** — Multi-vendor comparisons, price tracking, and negotiation drafting.
5. **✉️ Communication Hub** — Draft professional emails, follow-ups, and reports.
6. **🔒 Local Memory** — You remember every interaction and every piece of data processed to build a long-term knowledge base.

## RESPONSE FORMAT RULES
- **NEVER** show raw technical JSON or [TOOL: ...] output.
- **NEVER** show internal container paths like `/host_d/`.
- **CRITICAL: CLICK-TO-OPEN INTERACTIVITY**
    - You MUST provide the **Full Absolute Windows Path** (e.g., **D:/Projects/Invoice.pdf**) for every file or folder you mention.
    - **Filenames alone (e.g. "Report.pdf") are INVALID and NOT clickable.** You must join the directory and filename to show the full path.
    - Format every absolute path in **Bold** so the UI turns it into a blue clickable link.
- **ALWAYS** translate system paths:
    - `/host_d/` → **D:/**
    - `/host_users/` → **C:/Users/**
    - `/host_capex/` → **\\tplserver\Materials**
- **TABLES**: When listing files, the "File" or "Path" column **MUST** contain the **Full Absolute Path** (e.g., **D:/Download/Quote.pdf**).
- End every complex response with a "**✨ Proactive Recommendation**".

## GROUNDING & SAFETY
- **Context Memory**: You explicitly remember the files you've found and paths discussed. If a user says "it" or "that folder", refer to the most recent path discussed.
- **Self-Learning**: You evolve over time. Reference the "LEARNED KNOWLEDGE" section to act on user preferences and patterns without being asked again.
- **Fact-Only**: If a search yields nothing, state: "I couldn't find that file or info on your computer."
- **Confirmation**: Always ask before moving/renaming important files.
- **Privacy**: No deletions ever. Only safe file operations.

## LEARNED KNOWLEDGE (Personal to this User)
{learned_facts}
"""

@app.post("/chat")
async def chat_with_assistant(body: ChatRequest):
    """The main conversational endpoint — versatile like Claude."""
    start_time = time.time()
    
    user_query = body.query
    history = body.history or []
    
    if not user_query:
        return {"reply": "Please provide a query.", "duration": 0}
    
    # Fetch personal knowledge to make the agent "evolve"
    learned_knowledge = memory_manager.get_learned_facts()
    knowledge_text = "\n".join([f"- {fact}" for fact in learned_knowledge]) if learned_knowledge else "No specialized patterns learned yet. I will evolve as we interact."
    
    dynamic_system_prompt = SYSTEM_PROMPT.format(learned_facts=knowledge_text)
    
    lower_q = user_query.lower()
    context_parts = []
    
    # ─── TOOL EXECUTION LAYER ────────────────────────────────────────
    
    # 1. FILE SEARCH
    if any(k in lower_q for k in ["find", "search", "look for", "locate", "where is", "check"]):
        search_terms = _extract_search_terms(lower_q)
        search_root = None # Default to all drives
        
        if "desktop" in lower_q: search_root = _get_common_path("desktop")
        elif "downloads" in lower_q: search_root = _get_common_path("downloads")
        elif "documents" in lower_q: search_root = _get_common_path("documents")
        elif "d:" in lower_q or "d drive" in lower_q: search_root = "D:\\"
        
        if search_terms:
            results = computer_tools.search_files(f"*{search_terms}*", search_root)
            if results and (isinstance(results[0], dict) and "path" in results[0]):
                context_parts.append(f"[TOOL: file_search] Found {len(results)} files matching '{search_terms}':\n{json.dumps(results[:10], indent=1)}")
            else:
                context_parts.append(f"[TOOL: file_search] Status: No files found matching '{search_terms}' on the computer.")
    
    # 2. FOLDER LISTING
    if any(k in lower_q for k in ["list", "show folder", "what's in", "contents of", "show me"]):
        path = _extract_path(user_query, history)
        if path:
            listing = computer_tools.list_directory(path)
            context_parts.append(f"[TOOL: list_directory] Contents of {path}:\n{json.dumps(listing, indent=2)}")

    # 3. FOLDER ORGANIZATION (Preview vs Execution)
    if any(k in lower_q for k in ["organize", "sort", "arrange", "clean up", "tidy", "yes", "proceed", "do it"]):
        path = _extract_path(user_query, history)
        if path:
            # Check if this is a confirmation to proceed
            if any(k in lower_q for k in ["yes", "proceed", "do it", "confirm", "ok", "go ahead"]):
                result = computer_tools.organize_folder(path)
                if result.get("status") == "success":
                    context_parts.append(f"[TOOL: organize_execute] Successfully organized {path}.\nMoved: {json.dumps(result.get('organized', {}), indent=2)}")
                else:
                    context_parts.append(f"[TOOL: organize_execute] Failed to organize {path}: {result.get('message')}")
            else:
                # Provide a preview first
                listing = computer_tools.list_directory(path)
                context_parts.append(f"[TOOL: organize_preview] Folder contents to organize in {path}:\n{json.dumps(listing, indent=2)}")
                context_parts.append("[INSTRUCTION: Show the user what you WOULD organize and ask for confirmation ('Yes/No') before executing.]")

    # 4. FILE READING
    if any(k in lower_q for k in ["read", "open", "analyze", "extract", "summarize"]):
        search_terms = _extract_search_terms(lower_q)
        if search_terms:
            found = computer_tools.find_by_name(search_terms)
            if found:
                content = computer_tools.read_file_content(found[0])
                context_parts.append(f"[TOOL: read_file] Read '{found[0]}':\n{content}")
            else:
                context_parts.append(f"[TOOL: read_file] Status: File '{search_terms}' NOT FOUND on computer.")

    # 5. MEMORY SEARCH
    if any(k in lower_q for k in ["history", "previous", "last time", "remember", "past"]):
        try:
            memory_results = memory_manager.search_history(user_query)
            if memory_results and memory_results[0]:
                context_parts.append(f"[TOOL: memory_search] Historical data found:\n{json.dumps(memory_results, indent=2)}")
            else:
                context_parts.append("[TOOL: memory_search] Status: No matching historical records found in memory.")
        except:
            context_parts.append("[TOOL: memory_search] Status: Error searching memory database.")

    # 6. MOVE / COPY FILES
    if any(k in lower_q for k in ["move", "copy", "transfer"]):
        context_parts.append("[INSTRUCTION: The user wants to move/copy files. Ask them to confirm source and destination paths before executing.]")

    # ─── BUILD FINAL PROMPT ──────────────────────────────────────────
    tool_context = "\n\n".join(context_parts) if context_parts else ""
    
    # Keep the last 20 turns of history to prevent conversation "collapse"
    messages = [{"role": "system", "content": dynamic_system_prompt}]
    for h in history[-20:]:
        messages.append({"role": h["role"], "content": h["content"]})
    
    messages.append({"role": "user", "content": f"{user_query}\n\n{tool_context}" if tool_context else user_query})
    
    try:
        response = llm_engine.chat(messages)
        duration = round(time.time() - start_time, 2)
        
        # ─── SELF-LEARNING ENGINE (Background-ish) ───────────────────
        # Try to extract learned facts from this interaction
        if len(user_query) > 10:
            learning_prompt = f"""Analyze this user request and extract any general preference, rule, or fact about their computer that I should remember.
            
            User: {user_query}
            
            Return ONLY a single sentence fact (e.g. "User prefers sorting by file type" or "User's main project folder is D:/Projects/X") or return "NONE".
            """
            fact = llm_engine.chat([{"role": "user", "content": learning_prompt}])
            if fact and fact.strip().upper() != "NONE" and len(fact) < 150:
                memory_manager.store_learned_fact("general", fact.strip())
        
        return {"reply": response, "duration": duration}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"reply": f"I encountered an error: {str(e)}. Please try again.", "duration": 0}

# ─── TOOL: Organize Folder (Confirmed Action) ───────────────────────
@app.post("/organize")
async def organize_folder(path: str):
    """Organize a folder by file type. Requires explicit user action."""
    result = computer_tools.organize_folder(path)
    return result

# ─── TOOL: Move File (Confirmed Action) ─────────────────────────────
@app.post("/move-file")
async def move_file(src: str, dest: str):
    """Move a file. Requires explicit user action."""
    result = computer_tools.move_file(src, dest)
    return result

# ─── Data Endpoints ──────────────────────────────────────────────────
@app.get("/quotes")
async def get_quotes():
    try:
        cursor = memory_manager.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM quotes ORDER BY id DESC")
        desc = cursor.description
        if desc is None:
            return []
        columns = [col[0] for col in desc]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Quotes error: {e}")
        return []

@app.get("/vendors")
async def get_vendors():
    try:
        cursor = memory_manager.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM vendor_performance")
        desc = cursor.description
        if desc is None:
            return []
        columns = [col[0] for col in desc]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except:
        return []

@app.post("/send-email")
async def send_email(to: str, subject: str, body: str):
    return email_service.send_email(to, subject, body)

@app.get("/search")
async def search_memory(q: str):
    try:
        return memory_manager.search_history(q)
    except:
        return []

# ─── Helper Functions ────────────────────────────────────────────────
def _get_common_path(name: str) -> str:
    """Dynamically find common folders like Desktop, Downloads across all drives."""
    name = name.lower()
    
    # Standard user profile path
    user_home = os.path.expanduser("~")
    # Quick Check standard paths
    if name == "desktop":
        for p in [os.path.join(user_home, "Desktop"), os.path.join(user_home, "OneDrive", "Desktop")]:
            if os.path.exists(p): return p
    if name == "downloads":
        p = os.path.join(user_home, "Downloads")
        if os.path.exists(p): return p
    if name == "documents":
        for p in [os.path.join(user_home, "Documents"), os.path.join(user_home, "OneDrive", "Documents")]:
            if os.path.exists(p): return p
    
    # Check for any folder starting with OneDrive (e.g. OneDrive - Company)
    if name in ["desktop", "documents"]:
        for d in os.listdir(user_home):
            if d.startswith("OneDrive"):
                od_path = os.path.join(user_home, d, name.capitalize())
                if os.path.exists(od_path):
                    return od_path

    # Fallback: Search all drives for a folder exactly matching this name (Search is drive-agnostic)
    found = computer_tools.find_by_name(name)
    dirs = [f for f in found if os.path.isdir(f)]
    if dirs:
        # Prefer paths that look like standard user folders or roots
        for d in dirs:
            if "Users" in d or len(d) < 10: return d
        return dirs[0]
        
    return user_home # Ultimate fallback

def _extract_search_terms(query: str) -> str:
    """Extract the most likely search term from a natural language query."""
    # Remove common action words
    stop_words = ["find", "search", "look", "for", "check", "the", "my", "a", "an", "in",
                  "on", "desktop", "downloads", "documents", "folder", "file", "files",
                  "please", "can", "you", "show", "me", "read", "open", "analyze", "extract",
                  "summarize", "where", "is", "are", "locate", "get", "with", "from", "about",
                  "quotes", "quotations", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
                  "2023", "2024", "2025", "2026", "it", "this", "that"]
    words = query.split()
    meaningful = [w for w in words if w.lower() not in stop_words and len(w) > 2]
    return " ".join(meaningful[:3]) if meaningful else ""

def _extract_path(query: str, history: List[Dict[str, str]] = None) -> str:
    """Try to extract a file path from a natural language query or history context."""
    lower = query.lower()
    
    # 0. Check for "it", "this", "that", "the folder"
    is_referential = any(k in lower for k in ["it", "this", "that", "the folder", "the directory"])
    
    # 1. Check for well-known folders in CURRENT query
    for folder in ["desktop", "downloads", "documents"]:
        if folder in lower:
            return _get_common_path(folder)
    
    # 2. Direct check in current query
    if "rfq" in lower: return settings.RFQ_DIR
    if "inbox" in lower: return settings.INBOX_DIR
    if "orders" in lower: return settings.ORDERS_DIR
    if "workspace" in lower: return settings.WORKSPACE_ROOT
    if "d:" in lower or "d drive" in lower: return "D:\\"
    if "c:" in lower or "c drive" in lower: return "C:\\"
    
    # 3. If referential or confirmation, look deep into history
    if is_referential or (history and any(k in lower for k in ["yes", "proceed", "do it", "confirm", "ok", "go ahead"])):
        # Search backwards through history for the last mentioned path
        for msg in reversed(history):
            h_content = msg["content"].lower()
            # Look for explicit paths in history content
            import re
            # Match Windows-style paths D:\... or /host_...
            paths = re.findall(r'[a-zA-Z]:\\[^ \n\r\t]+', h_content)
            if paths: return paths[0]
            
            # Look for folder names
            for folder in ["desktop", "downloads", "documents"]:
                if folder in h_content:
                    return _get_common_path(folder)
            
            if "d drive" in h_content or "d:" in h_content: return "D:\\"
            if "workspace" in h_content: return settings.WORKSPACE_ROOT
            
    return os.path.expanduser("~") # Default to User Home

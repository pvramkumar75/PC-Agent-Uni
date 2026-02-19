# OmniMind — Setup Guide (For New Users)

## What is OmniMind?
A personal AI assistant that runs **on your machine**. When you use the shared link, it connects to your own PC to help you search files, analyze documents, and stay organized.

---

## Step 1: Get Your API Key
1. Go to: [https://platform.deepseek.com/](https://platform.deepseek.com/)
2. Create an account and get an **API Key**.
3. Create a file named `.env` in this folder and add:
   ```
   DEEPSEEK_API_KEY=sk-xxxx...
   ```

## Step 2: Run the Engine
You need to run the "brain" of the app on your computer so it can see your files.

**Option A (No Installation)**
1. Ensure you have [Python](https://www.python.org/) installed.
2. Double-click `run_local.py`.
3. It will install everything and start automatically.

**Option B (Docker)**
1. Open Docker Desktop.
2. Run `docker-compose up`.

---

## Step 3: Use the Universal Link
Once your engine is running:
1. Open the shared link (e.g., `https://omnimind-ui.vercel.app`).
2. Go to **Settings** (Gear icon in sidebar).
3. Ensure the URL is `http://localhost:8000`.
4. ✨ **Start chatting!**

---

## 🔍 Smart Features for You
- **"Check my Desktop"**: It automatically finds your Desktop on any drive (C:, D:, etc.).
- **"Organize Downloads"**: It will sort your files into neat folders.
- **"Analyze Quote"**: Summarizes any PDF or Excel quotation.

---

## Important Security Note
**Your files NEVER leave your computer.** The shared link is just a "Remote Control". All the heavy lifting and data storage happens locally on your machine.

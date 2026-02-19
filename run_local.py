import os
import sys
import subprocess
import webbrowser
import time

def run_command(command):
    print(f"Executing: {command}")
    return subprocess.run(command, shell=True)

def main():
    print("🚀 Starting OmniMind Universal Engine...")
    
    # 1. Check for Python
    print("Checking Python environment...")
    
    # 2. Install dependencies
    print("Installing/Updating dependencies...")
    run_command(f"{sys.executable} -m pip install -r backend/requirements.txt")
    
    # 3. Set environment variables if not present
    if not os.path.exists(".env"):
        print("⚠️ Warning: .env file not found. Creating a template...")
        with open(".env", "w") as f:
            f.write("DEEPSEEK_API_KEY=your_key_here\n")
        print("Please edit the .env file and add your DEEPSEEK_API_KEY.")
    
    # 4. Start the backend
    print("Starting Backend on http://localhost:8000 ...")
    
    # We use a subprocess for the backend so we can continue in this script
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd="backend"
    )
    
    # 5. Open the UI
    # In a real scenario, the user would use their shared Vercel link.
    # For now, we point to localhost:3000 as a fallback or the Vercel app.
    ui_url = "http://localhost:3000" # Local dev
    # ui_url = "https://your-omnimind-app.vercel.app" # Production
    
    print(f"\n✨ OmniMind is ready!")
    print(f"🔗 UI Access: {ui_url}")
    print(f"Press Ctrl+C to stop the engine.")
    
    time.sleep(2)
    webbrowser.open(ui_url)
    
    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping OmniMind...")
        backend_proc.terminate()

if __name__ == "__main__":
    main()

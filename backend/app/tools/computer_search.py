import os
import glob
import shutil
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ComputerTools:
    """Full-featured computer interaction tools for file search, organization, and reading."""

    @staticmethod
    def get_all_drives() -> List[str]:
        """Detect all available drives on Windows or return root on Linux."""
        import platform
        if platform.system() == "Windows":
            import string
            from ctypes import windll
            drives = []
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
            return drives
        return ["/"]

    @staticmethod
    def get_universal_roots() -> List[str]:
        """Get standard root directories like User folders and all drives."""
        roots = []
        # 1. User profile folders
        user_profile = os.path.expanduser("~")
        roots.append(user_profile)
        
        # 2. All logical drives
        try:
            roots.extend(ComputerTools.get_all_drives())
        except:
            pass
        
        # 3. Specific workspace if present
        if os.path.exists("/workspace"): roots.append("/workspace")
        
        # Clean and return unique existing directories
        valid_roots = []
        for r in set(roots):
            if os.path.isdir(r):
                valid_roots.append(r)
        return valid_roots

    # ─── SEARCH & DISCOVER ─────────────────────────────────────────────

    @staticmethod
    def list_directory(path: str, max_items: int = 50) -> Dict[str, Any]:
        """List contents of a directory with file metadata."""
        try:
            # Handle user path expansion (e.g. ~)
            path = os.path.expanduser(path)
            if not os.path.isdir(path):
                return {"error": f"Not a directory: {path}"}
            
            items = []
            for entry in os.scandir(path):
                try:
                    stat = entry.stat()
                    items.append({
                        "name": entry.name,
                        "type": "dir" if entry.is_dir() else "file",
                        "size_kb": round(stat.st_size / 1024, 1) if entry.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    })
                except:
                    items.append({"name": entry.name, "type": "unknown"})
            
            items.sort(key=lambda x: (x["type"] == "file", x["name"]))
            return {
                "path": path,
                "total_items": len(items),
                "items": items[:max_items]
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def search_files(pattern: str, root_dir: str = None, max_results: int = 25) -> List[Dict[str, str]]:
        """Search for files matching a pattern using os.walk for better control."""
        if root_dir is None:
            # Default to scanning all drives if no root is provided
            roots = ComputerTools.get_universal_roots()
            results = []
            for r in roots:
                results.extend(ComputerTools.search_files(pattern, r, max_results - len(results)))
                if len(results) >= max_results:
                    break
            return results

        results = []
        pattern_lower = pattern.replace("*", "").lower()
        
        # Directories to skip to prevent hanging
        skip_dirs = {
            'node_modules', '__pycache__', '.git', 'AppData', '$Recycle.Bin', 
            'Windows', 'Program Files', 'Program Files (x86)', 'System Volume Information'
        }
        
        try:
            for root, dirs, files in os.walk(root_dir):
                # Filter directories in-place to skip them
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in skip_dirs]
                
                for name in files:
                    if pattern_lower in name.lower():
                        f_path = os.path.join(root, name)
                        try:
                            stat = os.stat(f_path)
                            results.append({
                                "path": f_path.replace("\\", "/"),
                                "name": name,
                                "size_kb": round(stat.st_size / 1024, 1),
                                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                            })
                        except:
                            results.append({"path": f_path.replace("\\", "/"), "name": name})
                        
                        if len(results) >= max_results:
                            return results
            return results
        except Exception as e:
            logger.error(f"Search error in {root_dir}: {e}")
            return [{"error": str(e)}]

    @staticmethod
    def find_by_name(name_fragment: str, root_dirs: List[str] = None) -> List[str]:
        """Find files or folders containing a name fragment across multiple root directories."""
        if root_dirs is None:
            root_dirs = ComputerTools.get_universal_roots()
        
        found = []
        for root in root_dirs:
            if not os.path.isdir(root):
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(root):
                    # Skip hidden and system directories
                    dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git', 'AppData', '$Recycle.Bin']]
                    
                    # Check files
                    for fname in filenames:
                        if name_fragment.lower() in fname.lower():
                            found.append(os.path.join(dirpath, fname))
                            if len(found) >= 20: return found
                    
                    # Check directories (new: for finding "Desktop" etc)
                    for dname in dirnames:
                        if name_fragment.lower() == dname.lower():
                            found.append(os.path.join(dirpath, dname))
                            if len(found) >= 20: return found
            except:
                continue
        return found

    # ─── FILE OPERATIONS (with safety) ──────────────────────────────────

    @staticmethod
    def read_file_content(file_path: str, max_chars: int = 5000) -> str:
        """Read file content using the file processor."""
        from app.tools.file_processor import file_processor
        try:
            content = file_processor.read_file(file_path)
            if len(content) > max_chars:
                return content[:max_chars] + f"\n\n... [Truncated. Full file is {len(content)} chars]"
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @staticmethod
    def move_file(src: str, dest_dir: str) -> Dict[str, str]:
        """Move a file to a destination directory."""
        try:
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, os.path.basename(src))
            shutil.move(src, dest_path)
            logger.info(f"Moved {src} -> {dest_path}")
            return {"status": "success", "from": src, "to": dest_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def copy_file(src: str, dest_dir: str) -> Dict[str, str]:
        """Copy a file to a destination directory."""
        try:
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, os.path.basename(src))
            shutil.copy2(src, dest_path)
            logger.info(f"Copied {src} -> {dest_path}")
            return {"status": "success", "from": src, "to": dest_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def create_folder(path: str) -> Dict[str, str]:
        """Create a new folder (and any parents)."""
        try:
            os.makedirs(path, exist_ok=True)
            return {"status": "success", "path": path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def rename_file(src: str, new_name: str) -> Dict[str, str]:
        """Rename a file in the same directory."""
        try:
            parent = os.path.dirname(src)
            dest = os.path.join(parent, new_name)
            os.rename(src, dest)
            return {"status": "success", "from": src, "to": dest}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_folder_tree(path: str, depth: int = 2) -> str:
        """Get a tree-like view of a directory."""
        lines = []
        def _walk(p, prefix, current_depth):
            if current_depth > depth:
                return
            try:
                entries = sorted(os.scandir(p), key=lambda e: (e.is_file(), e.name))
                for i, entry in enumerate(entries[:20]):
                    is_last = i == len(entries[:20]) - 1
                    connector = "└── " if is_last else "├── "
                    lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
                    if entry.is_dir() and current_depth < depth:
                        extension = "    " if is_last else "│   "
                        _walk(entry.path, prefix + extension, current_depth + 1)
            except:
                pass
        
        lines.append(f"{path}/")
        _walk(path, "", 1)
        return "\n".join(lines)

    # ─── ORGANIZE FILES ─────────────────────────────────────────────────

    @staticmethod
    def organize_folder(path: str, rules: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """
        Organize files in a folder by type into subfolders.
        Default rules sort by common procurement file types.
        """
        if rules is None:
            rules = {
                "Quotations": [".pdf", ".docx"],
                "Spreadsheets": [".xlsx", ".xls", ".csv"],
                "Images": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".svg"],
                "Documents": [".doc", ".txt", ".rtf", ".pdf", ".docx", ".xlsx", ".pptx"], # Catch-all docs
                "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
                "Shortcuts": [".lnk", ".url"],
                "Scripts": [".py", ".bat", ".sh", ".js"],
            }
        
        moved = {}
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    ext = os.path.splitext(entry.name)[1].lower()
                    for folder_name, extensions in rules.items():
                        if ext in extensions:
                            dest_dir = os.path.join(path, folder_name)
                            os.makedirs(dest_dir, exist_ok=True)
                            dest = os.path.join(dest_dir, entry.name)
                            shutil.move(entry.path, dest)
                            moved.setdefault(folder_name, []).append(entry.name)
                            break
            return {"status": "success", "organized": moved, "total_moved": sum(len(v) for v in moved.values())}
        except Exception as e:
            return {"status": "error", "message": str(e)}

computer_tools = ComputerTools()

import os
import shutil
import subprocess

def build():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    backend_dir = os.path.join(root_dir, "backend")
    
    # 1. Ensure frontend is built
    print("Building frontend...")
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
    
    frontend_dist = os.path.join(frontend_dir, "dist")
    backend_frontend_dist = os.path.join(backend_dir, "frontend_dist")
    
    # 2. Copy built frontend to backend directory
    print("Copying frontend static files to backend...")
    if os.path.exists(backend_frontend_dist):
        shutil.rmtree(backend_frontend_dist)
    shutil.copytree(frontend_dist, backend_frontend_dist)
    
    # 3. Run PyInstaller
    print("Running PyInstaller...")
    # Add frontend_dist as a data folder to be bundled
    data_separator = os.pathsep  # ':' on Unix, ';' on Windows
    add_data_arg = f"{backend_frontend_dist}{data_separator}frontend_dist"
    
    # We must run pyinstaller from the backend directory so main.py is the entry point
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=CV_Optimizer",
        "--onefile",
        "--add-data", add_data_arg,
        "--clean",
        "main.py"
    ]
    
    # Needs to be run inside the virtual environment context, or we can just use subprocess
    subprocess.run(pyinstaller_cmd, cwd=backend_dir, check=True)
    
    print("\n--- Build Complete ---")
    print(f"Executable created in: {os.path.join(backend_dir, 'dist', 'CV_Optimizer')}")

if __name__ == "__main__":
    build()

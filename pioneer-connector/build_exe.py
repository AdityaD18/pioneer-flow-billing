import os
import sys
import subprocess

def build_pioneer_connector_exe():
    """
    Builds standalone executable PioneerConnector.exe using PyInstaller.
    """
    connector_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(connector_dir, "main.py")
    project_root = os.path.dirname(connector_dir)
    dist_dir = os.path.join(project_root, "dist")
    build_dir = os.path.join(project_root, "build")

    print(f"[Build] Compiling PioneerConnector.exe from {main_py}...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name=PioneerConnector",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        "--add-data", f"{os.path.join(connector_dir, 'config')}{os.path.pathsep}config",
        main_py
    ]

    try:
        subprocess.check_call(cmd, cwd=connector_dir)
        exe_path = os.path.join(dist_dir, "PioneerConnector", "PioneerConnector.exe")
        print(f"[SUCCESS] PioneerConnector.exe compiled at: {exe_path}")
        return exe_path
    except Exception as e:
        print(f"[ERROR] PyInstaller build failed: {e}")
        return None

if __name__ == "__main__":
    build_pioneer_connector_exe()

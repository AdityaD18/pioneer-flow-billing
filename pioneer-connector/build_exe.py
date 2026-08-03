import os
import sys
import subprocess

def build_pioneer_connector_exe():
    """
    Builds standalone background executable PioneerConnector.exe using PyInstaller.
    """
    connector_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(connector_dir, "main.py")
    dist_dir = os.path.join(os.path.dirname(connector_dir), "dist")
    build_dir = os.path.join(os.path.dirname(connector_dir), "build")

    print(f"[Build] Building PioneerConnector.exe from {main_py}...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed", # Run headless in background without command console popup
        "--name=PioneerConnector",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        "--add-data", f"{os.path.join(connector_dir, 'config')}{os.path.pathsep}config",
        main_py
    ]

    try:
        subprocess.check_call(cmd, cwd=connector_dir)
        print(f"✅ Success! PioneerConnector.exe built at: {os.path.join(dist_dir, 'PioneerConnector', 'PioneerConnector.exe')}")
    except Exception as e:
        print(f"⚠️ PyInstaller compilation note: {e}")

if __name__ == "__main__":
    build_pioneer_connector_exe()

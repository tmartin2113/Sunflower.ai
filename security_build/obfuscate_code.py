import os
import shutil
import subprocess
import sys
from pathlib import Path

def obfuscate_project(source_dir: Path, output_dir: Path):
    """
    Obfuscates the Python source code of the project using PyArmor.

    This function cleans the output directory, then calls the PyArmor
    command-line tool to obfuscate the entire source directory.

    Args:
        source_dir: The path to the source code directory (e.g., 'src').
        output_dir: The path where the obfuscated code will be placed.
    
    Returns:
        True if obfuscation was successful, False otherwise.
    """
    if not source_dir.exists():
        print(f"Error: Source directory not found at '{source_dir}'")
        return False

    # Clean the output directory
    if output_dir.exists():
        print(f"Cleaning existing output directory: {output_dir}")
        shutil.rmtree(output_dir)
    
    print(f"Obfuscating code from '{source_dir}' to '{output_dir}'...")

    # Construct the pyarmor command
    # We target the pyarmor executable directly if it's in the scripts path
    # This avoids issues where the scripts path isn't in the system's PATH env var.
    pyarmor_executable = "pyarmor"
    if sys.platform == "win32":
        # A common location for user-installed Python scripts on Windows
        scripts_path = Path(os.environ["APPDATA"]) / "Python" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "Scripts" / "pyarmor.exe"
        if scripts_path.exists():
            pyarmor_executable = str(scripts_path)

    command = [
        pyarmor_executable,
        "obfuscate",
        "--recursive",
        "--output", str(output_dir),
        str(source_dir)
    ]

    try:
        # We capture the output to show it in case of an error
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        print("PyArmor obfuscation completed successfully.")
        print(result.stdout)
        return True
    except FileNotFoundError:
        print(f"Error: '{pyarmor_executable}' command not found.")
        print("Please ensure PyArmor is installed and accessible in your system's PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print("Error during PyArmor obfuscation.")
        print(f"Return Code: {e.returncode}")
        print("--- PyArmor STDOUT ---")
        print(e.stdout)
        print("--- PyArmor STDERR ---")
        print(e.stderr)
        return False

if __name__ == '__main__':
    # Define project paths relative to this script
    project_root = Path(__file__).parent.parent
    source_path = project_root / 'src'
    build_path = project_root / 'build'
    obfuscated_code_path = build_path / 'obfuscated_src'

    print("--- Starting Code Obfuscation ---")
    if obfuscate_project(source_path, obfuscated_code_path):
        print("\nObfuscation process finished successfully.")
    else:
        print("\nObfuscation process failed.")

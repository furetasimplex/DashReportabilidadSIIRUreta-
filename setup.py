import os
import subprocess
import sys

# Nombre del virtual environment
venv_folder = "venvAppRipio"

# Verificar si ya existe
if not os.path.isdir(venv_folder):
    print(f"No se encontró {venv_folder}. Creando virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", venv_folder])
else:
    print(f"Virtual environment '{venv_folder}' ya existe.")

# Activar virtual environment según sistema operativo
if os.name == "nt":  # Windows
    activate_script = os.path.join(venv_folder, "Scripts", "activate")
else:  # Linux / Mac
    activate_script = os.path.join(venv_folder, "bin", "activate")

# Instalar requirements.txt
print("Instalando paquetes desde requirements.txt...")
subprocess.check_call([os.path.join(venv_folder, "Scripts" if os.name == "nt" else "bin", "python"),
                       "-m", "pip", "install", "--upgrade", "pip"])
subprocess.check_call([os.path.join(venv_folder, "Scripts" if os.name == "nt" else "bin", "python"),
                       "-m", "pip", "install", "-r", "requirements.txt"])

print("¡Listo! Virtual environment creado y dependencias instaladas.")

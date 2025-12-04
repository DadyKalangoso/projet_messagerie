import time
import os

from config import get_config
from format import read_new_lines
from commande import handle_exec_request
from file_transfer import check_new_files, list_user_files

import re

def process_exec_line(line, current_user, shared_file):

    #regex pour extraire sender + content proprement
    pattern = r"^\d{4}-\d{2}-\d{2} .* ?[–-] (.*?) : (.*)$"
    match = re.match(pattern, line)

    if not match:
        print("[DEBUG] REGEX FAIL:", line)
        return

    sender = match.group(1).strip()
    content = match.group(2).strip()

    # On vérifie que c’est bien une commande exec
    if not content.startswith("@exec"):
        return

    # Extraction @exec <dest> <commande>
    parts = content.split(maxsplit=2)
    if len(parts) < 3:
        print("[DEBUG] BAD EXEC FORMAT:", content)
        return

    dest_user = parts[1].strip()
    command = parts[2].strip()

    print("[DEBUG] SENDER:", sender)
    print("[DEBUG] DEST_USER:", dest_user)
    print("[DEBUG] CURRENT_USER:", current_user)
    print("[DEBUG] COMMAND:", command)

    # Sécurité : ce n’est pas pour nous
    if dest_user != current_user:
        return

    # On lance la demande
    handle_exec_request(sender, dest_user, current_user, command, shared_file)


# ---------------------- Programme principal ----------------------

cfg = get_config()
shared_file = cfg["shared_file"]
downloads_dir = cfg["downloads_dir"]
interval = float(cfg["interval"])

# Nom de l'utilisateur
current_user = input("Entrez votre nom d'utilisateur : ").strip()

# Prépare le fichier partagé
if not os.path.isfile(shared_file):
    open(shared_file, 'w').close()

f = open(shared_file, 'r', encoding='utf-8')
last_pos = f.seek(0, os.SEEK_END)

# Liste des fichiers reçus
known_files = list_user_files(current_user, downloads_dir)

print("Lecture du chat en cours...\n")

while True:
    # Lire uniquement les nouvelles lignes
    lines, last_pos = read_new_lines(f, last_pos)

    for line in lines:
        line = line.rstrip()
        print(line)
        
        if "@exec" in line:
            print("[DEBUG] @exec CALLED")
            process_exec_line(line, current_user, shared_file)

    # Vérifier les nouveaux fichiers
    new_files, known_files = check_new_files(current_user, downloads_dir, known_files)
    for fname in new_files:
        print(f"[INFO] Nouveau fichier reçu : {fname}")

    time.sleep(interval)
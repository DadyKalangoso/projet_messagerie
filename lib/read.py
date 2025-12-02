import time
import os

from config import get_config
from utils import read_new_lines
from commande import handle_exec_request
from file_transfer import check_new_files, list_user_files


def process_exec_line(line, current_user, shared_file):
    """
    Analyse une ligne contenant @exec et lance handle_exec_request si c'est pour nous.
    Format du log :
    YYYY-MM-DD ... – sender : @exec destinataire commande
    """
    try:
        meta, content = line.split(":", 1)
        content = content.strip()

        if not content.startswith("@exec"):
            return

        parts = content.split(maxsplit=2)
        # parts = ["@exec", "<dest_user>", "<commande>"]

        sender = meta.split("–")[1].strip()
        dest_user = parts[1]
        command = parts[2]

        handle_exec_request(sender, dest_user, current_user, command, shared_file)

    except Exception as e:
        print(f"[ERREUR] Impossible de traiter la commande exec : {e}")


# ---------------------- Programme principal ----------------------

cfg = get_config()
shared_file = cfg["shared_file"]
downloads_dir = cfg["downloads_dir"]
poll_interval = float(cfg["poll_interval"])

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
            process_exec_line(line, current_user, shared_file)

    # Vérifier les nouveaux fichiers
    new_files, known_files = check_new_files(current_user, downloads_dir, known_files)
    for fname in new_files:
        print(f"[INFO] Nouveau fichier reçu : {fname}")

    time.sleep(poll_interval)
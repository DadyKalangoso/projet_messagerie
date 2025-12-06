# KALANGOSO KANGELA - RAYANE BADKOUF
import json
import os

def read_config(path='chat.json'):
    """
    Lit un fichier JSON et retourne un dict Python.
    Si le fichier n'existe pas, renvoie un dict vide.
    """
    if not os.path.isfile(path):
        print(f"[ERROR] Fichier de configuration introuvable : {path}")
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Impossible de lire le fichier JSON : {e}")
        return {}


def get_config():
    """
    Récupère la configuration à partir de chat.json,
    en ajoutant des valeurs par défaut si certaines clés manquent.
    Retourne toujours un dictionnaire propre.
    """
    config = read_config()

    # valeurs par défaut
    defaults = {
        "shared_file": "//DESKTOP-LPSLR66/dossier_partage/shared_chat.log",
        "downloads_dir": "//DESKTOP-LPSLR66/dossier_partage/file",
        "interval": 0.5
    }

    # appliquer les valeurs par défaut si absentes
    for key, value in defaults.items():
        if key not in config:
            config[key] = value

    return config
def read_config(path='chat.conf'):
    cfg = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith('#'):
                    continue

                if '=' in line:
                    key, value = line.split('=', 1)
                    cfg[key.strip()] = value.strip()

    except FileNotFoundError:
        print(f"[ERROR] Fichier de configuration introuvable : {path}")

    return cfg


def get_config():
    """
    Lit la configuration et assigne des valeurs par défaut si nécessaire.
    """
    cfg = read_config()

    cfg.setdefault("shared_file", "//192.168.1.101/dossier_partage/shared_chat.log")
    cfg.setdefault("downloads_dir", "//192.168.1.101/dossier_partage/file")
    cfg.setdefault("poll_interval", "0.5")

    return cfg
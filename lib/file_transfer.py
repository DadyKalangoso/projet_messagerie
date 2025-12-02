import os
from utils import ensure_dir

CHUNK_SIZE = 8192  # 8 KB

def send_file(src_path, dest_user, downloads_dir):
    """
    Envoie un fichier src_path vers Downloads/dest_user/.
    Retourne (nom_du_fichier, chemin_destination).
    """
    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"Le fichier {src_path} n'existe pas.")

    filename = os.path.basename(src_path)
    user_dir = os.path.join(downloads_dir, dest_user)

    ensure_dir(user_dir)

    dest_path = os.path.join(user_dir, filename)

    # Copier à la main en binaire
    with open(src_path, 'rb') as src, open(dest_path, 'wb') as dst:
        while True:
            chunk = src.read(CHUNK_SIZE)
            if not chunk:
                break
            dst.write(chunk)
            dst.flush()

    return filename, dest_path


def list_user_files(username, downloads_dir):
    """
    Retourne la liste des fichiers dans Downloads/<username>.
    """
    user_dir = os.path.join(downloads_dir, username)
    if not os.path.isdir(user_dir):
        return []
    return os.listdir(user_dir)


def check_new_files(username, downloads_dir, known_files):
    """
    Compare les fichiers dans Downloads/<username> avec known_files.
    Retourne les nouveaux fichiers et la liste complète.
    """
    current_files = set(list_user_files(username, downloads_dir))
    new_files = current_files - set(known_files)
    return list(new_files), list(current_files)
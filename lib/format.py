from datetime import datetime
import os

def format_time():
    """
    Retourne la date/heure actuelle au format :
    YYYY-MM-DD HH:MM:SS.milliseconds
    """
    return datetime.now().isoformat(sep=' ', timespec='milliseconds')

def format_msg(username, text):
    """
    Formate un message selon le format imposé dans le projet.
    """
    return f"{format_time()} - {username} : {text}\n"

def make_dir(path):
    """
    Crée un dossier s'il n'existe pas déjà.
    """
    os.makedirs(path, exist_ok=True)

def read_new_lines(file_obj, last_pos):
    """
    Lit uniquement les nouvelles lignes ajoutées depuis last_pos.
    Retourne (liste_des_lignes, nouvelle_position).
    """
    file_obj.seek(last_pos)
    lines = file_obj.readlines()
    new_pos = file_obj.tell()
    return lines, new_pos
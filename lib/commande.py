import subprocess
from format import format_msg
import time

def ask_exec_permission(sender, command):
    """
    Demande à l'utilisateur s'il accepte d'exécuter la commande reçue.
    """
    print("[DEBUG] ask_exec_permission CALLED")
    time.sleep(0.05)
    print(f"[EXEC] {sender} veut exécuter : {command}")
    resp = input("Accepter ? (y/N) : ").strip().lower()
    return resp == 'y'


def execute_command(command):
    """
    Exécute la commande système demandée sur le PC du destinataire.
    """
    try:
        subprocess.Popen(command, shell=True)
        return True
    except Exception as e:
        print(f"[ERREUR EXEC] {e}")
        return False


def handle_exec_request(sender, dest_user, current_user, command, shared_file):
    """
    Gère une demande @exec envoyée dans le chat.
    """
    print("[DEBUG] ask_exec_permission CALLED")
    # Ce n'est pas pour cet utilisateur
    if dest_user != current_user:
        return

    allowed = ask_exec_permission(sender, command)

    with open(shared_file, 'a', encoding='utf-8') as f:
        if allowed:
            f.write(format_msg(current_user, f"[EXEC] Accepted command from {sender}: {command}"))
            execute_command(command)
        else:
            f.write(format_msg(current_user, f"[EXEC] Refused command from {sender}: {command}"))
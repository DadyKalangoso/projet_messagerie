from config import get_config
from utils import format_msg
from file_transfer import send_file

# Charger la configuration
cfg = get_config()
shared_file = cfg["shared_file"]
downloads_dir = cfg["downloads_dir"]

# Demander le nom d'utilisateur
username = input("Entrez votre nom d'utilisateur : ").strip()

# Message de connexion
with open(shared_file, 'a', encoding='utf-8') as f:
    f.write(format_msg(username, f"{username} joined the chat"))

print("Vous pouvez maintenant écrire des messages.")
print("Commandes : @exit, @send <fichier> <user>, @exec <user> <commande>")

# Boucle principale
while True:
    text = input()

    # Quitter
    if text.strip() == "@exit":
        with open(shared_file, 'a', encoding='utf-8') as f:
            f.write(format_msg(username, f"{username} left the chat"))
        break

    # Envoi de fichier
    elif text.startswith("@send "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            print("[ERREUR] Format : @send <fichier> <destinataire>")
            continue

        filepath = parts[1]
        dest_user = parts[2]

        try:
            filename, saved_path = send_file(filepath, dest_user, downloads_dir)
            with open(shared_file, 'a', encoding='utf-8') as f:
                f.write(format_msg(username, f"[FILE] Sent {filename} to {dest_user}"))
            print(f"[OK] Fichier envoyé vers {dest_user}")

        except Exception as e:
            print(f"[ERREUR] Impossible d'envoyer le fichier : {e}")

    # Commande @exec
    elif text.startswith("@exec "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            print("[ERREUR] Format : @exec <user> <commande>")
            continue
        
        dest_user = parts[1]
        command = parts[2]

        with open(shared_file, 'a', encoding='utf-8') as f:
            f.write(format_msg(username, f"@exec {dest_user} {command}"))

        print(f"[OK] Demande d'exécution envoyée à {dest_user}")

    # Message normal
    else:
        with open(shared_file, 'a', encoding='utf-8') as f:
            f.write(format_msg(username, text))
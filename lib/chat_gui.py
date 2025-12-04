import sys
import os
import json
import re
import subprocess

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QMessageBox, QLabel, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot


# ============================================================
# CONFIG
# ============================================================

def get_config(path="chat.json"):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config introuvable: {path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    cfg.setdefault("shared_file", "shared_chat.log")
    cfg.setdefault("poll_interval", 0.5)
    return cfg



# ============================================================
# THREAD DE LECTURE (Read.py intégré proprement)
# ============================================================

class ReaderThread(QThread):
    new_message = pyqtSignal(str)
    exec_request = pyqtSignal(str, str)  # sender, command

    def __init__(self, shared_file, current_user):
        super().__init__()
        self.shared_file = shared_file
        self.current_user = current_user
        self.running = True

    def parse_exec(self, line):
        """
        Détection propre du @exec via REGEX stable.
        """
        pattern = r"^\d{4}-\d{2}-\d{2} .* ?[–-] (.*?) : (.*)$"
        m = re.match(pattern, line)

        if not m:
            return

        sender = m.group(1).strip()
        content = m.group(2).strip()

        if not content.startswith("@exec"):
            return

        parts = content.split(maxsplit=2)
        if len(parts) < 3:
            return

        dest = parts[1].strip()
        command = parts[2].strip()

        if dest == self.current_user:  # commande destinée à ici
            self.exec_request.emit(sender, command)

    def run(self):
        if not os.path.isfile(self.shared_file):
            with open(self.shared_file, "w", encoding="utf-8") as f:
                pass

        with open(self.shared_file, "r", encoding="utf-8") as f:
            f.seek(0, 2)

            while self.running:
                line = f.readline()
                if line:
                    clean = line.rstrip("\n")
                    self.new_message.emit(clean)
                    self.parse_exec(clean)
                else:
                    self.msleep(int(100))



# ============================================================
# THREAD D’EXÉCUTION DES COMMANDES @exec
# ============================================================

class ExecWorker(QThread):
    def __init__(self):
        super().__init__()
        self.queue = []

    def enqueue(self, cmd):
        self.queue.append(cmd)
        if not self.isRunning():
            self.start()

    def run(self):
        while self.queue:
            cmd = self.queue.pop(0)
            try:
                subprocess.Popen(cmd, shell=True)
            except Exception as e:
                print("[EXEC ERROR]", e)



# ============================================================
# ÉCRITURE (chat.py intégré proprement)
# ============================================================

def write_message(username, text, shared_file):
    from datetime import datetime
    with open(shared_file, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} – {username} : {text}\n")



# ============================================================
# INTERFACE (UI principale)
# ============================================================

class ChatWindow(QMainWindow):
    def __init__(self, username):
        super().__init__()

        self.username = username
        self.cfg = get_config()
        self.shared_file = self.cfg["shared_file"]

        self.setWindowTitle("Messagerie PyQt6")
        self.resize(900, 550)

        self.exec_worker = ExecWorker()

        # Layout principal
        root = QWidget()
        root_layout = QHBoxLayout()
        root.setLayout(root_layout)
        self.setCentralWidget(root)

        # =====================================================
        # COLONNE GAUCHE : zone de chat
        # =====================================================

        left_layout = QVBoxLayout()

        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setPlaceholderText("Aucun message pour le moment...")

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Tapez votre message...")
        self.input_box.returnPressed.connect(self.send_message)

        btn_send = QPushButton("Envoyer")
        btn_send.clicked.connect(self.send_message)

        left_layout.addWidget(self.chat_view)
        left_layout.addWidget(self.input_box)
        left_layout.addWidget(btn_send)

        # =====================================================
        # COLONNE DROITE : Fonctions
        # =====================================================

        right_layout = QVBoxLayout()

        lbl_f = QLabel("Fonctions")
        lbl_f.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_f.setStyleSheet("font-weight: bold; font-size: 16px;")

        btn_exec = QPushButton("@exec")
        btn_exec.clicked.connect(self.ask_exec)

        right_layout.addWidget(lbl_f)
        right_layout.addWidget(btn_exec)
        right_layout.addStretch()

        # Ajout des deux colonnes
        root_layout.addLayout(left_layout, 4)
        root_layout.addLayout(right_layout, 1)

        # =====================================================
        # THREAD LECTURE → démarre après interface
        # =====================================================

        self.reader = ReaderThread(self.shared_file, self.username)
        self.reader.new_message.connect(self.append_message)
        self.reader.exec_request.connect(self.on_exec_request)
        self.reader.start()

    # =========================================================
    # UI CALLBACKS
    # =========================================================

    @pyqtSlot()
    def send_message(self):
        msg = self.input_box.text().strip()
        if not msg:
            return

        write_message(self.username, msg, self.shared_file)
        self.input_box.clear()

    @pyqtSlot(str)
    def append_message(self, text):
        self.chat_view.append(text)

    def ask_exec(self):
        target, ok = QInputDialog.getText(self, "@exec", "Utilisateur cible :")
        if not ok or not target.strip():
            return

        cmd, ok2 = QInputDialog.getText(self, "Commande", "Commande à exécuter :")
        if not ok2 or not cmd.strip():
            return

        write_message(self.username, f"@exec {target} {cmd}", self.shared_file)

    # =========================================================
    # Quand quelqu’un nous envoie @exec DEST command
    # =========================================================

    def on_exec_request(self, sender, command):
        reply = QMessageBox.question(
            self,
            "Demande d'exécution",
            f"{sender} veut exécuter :\n\n{command}\n\nAccepter ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            write_message(self.username, f"[EXEC] accepted {command}", self.shared_file)
            self.exec_worker.enqueue(command)
        else:
            write_message(self.username, f"[EXEC] refused {command}", self.shared_file)




# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)

    user, ok = QInputDialog.getText(None, "Connexion", "Nom d'utilisateur :")
    if not ok or not user.strip():
        sys.exit()

    win = ChatWindow(user.strip())
    win.show()

    sys.exit(app.exec())
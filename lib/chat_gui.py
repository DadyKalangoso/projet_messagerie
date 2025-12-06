# chat_gui.py
# Interface PyQt6 + intégration du moteur (read/write/@send/@exec)
# KALANGOSO KANGELA - RAYANE BADKOUF
import os
import sys
import json
import re
import time
import subprocess
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QMessageBox, QLabel, QInputDialog, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot

# -------------------------
# Config loader (JSON)
# -------------------------
def load_config(path="chat.json"):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("shared_file", "shared_chat.log")
    cfg.setdefault("downloads_dir", "file")
    cfg.setdefault("poll_interval", 0.5)
    return cfg

# -------------------------
# Utilitaires (format, dirs)
# -------------------------
def now_timestamp():
    return datetime.now().isoformat(sep=' ', timespec='microseconds')

def format_msg(username, text):
    # use simple dash '-' for robustness
    return f"{now_timestamp()} - {username} : {text}\n"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# -------------------------
# File transfer utilities (copy in chunks)
# -------------------------
CHUNK_SIZE = 8192

def send_file_binary(src_path, dest_user, downloads_dir):
    """
    Copy src_path into downloads_dir/<dest_user>/ keeping filename.
    Returns filename, dest_path
    """
    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"File not found: {src_path}")

    filename = os.path.basename(src_path)
    user_dir = os.path.join(downloads_dir, dest_user)
    ensure_dir(user_dir)
    dest_path = os.path.join(user_dir, filename)

    with open(src_path, "rb") as src, open(dest_path, "wb") as dst:
        while True:
            chunk = src.read(CHUNK_SIZE)
            if not chunk:
                break
            dst.write(chunk)
            dst.flush()

    return filename, dest_path

def list_user_files(username, downloads_dir):
    user_dir = os.path.join(downloads_dir, username)
    if not os.path.isdir(user_dir):
        return []
    return os.listdir(user_dir)

def check_new_files(username, downloads_dir, known_files):
    current = set(list_user_files(username, downloads_dir))
    new = current - set(known_files)
    return list(new), list(current)

# -------------------------
# ReaderThread : lit shared_file, émet new_message et exec_request
# -------------------------
class ReaderThread(QThread):
    new_message = pyqtSignal(str)          # line text
    exec_request = pyqtSignal(str, str)    # sender, command
    new_file = pyqtSignal(str)             # filename

    def __init__(self, shared_file, downloads_dir, current_user, poll_interval=0.5):
        super().__init__()
        self.shared_file = shared_file
        self.downloads_dir = downloads_dir
        self.current_user = current_user
        self.poll_interval = float(poll_interval)
        self._running = True

    def stop(self):
        self._running = False

    def parse_line_for_exec(self, line):
        """
        Robust parsing: lines form:
        YYYY-MM-DD hh:mm:ss.micro - sender : message
        Accepts '-' or '–' in separator.
        """
        pattern = r"^(\d{4}-\d{2}-\d{2} .*?) ?[–-] (.*?) : (.*)$"
        m = re.match(pattern, line)
        if not m:
            return
        sender = m.group(2).strip()
        content = m.group(3).strip()

        # detect @exec
        if content.startswith("@exec"):
            parts = content.split(maxsplit=2)
            if len(parts) >= 3:
                _, dest, cmd = parts
                if dest == self.current_user:
                    # don't execute here; ask GUI
                    self.exec_request.emit(sender, cmd)

    def run(self):
        # ensure path exists
        if not os.path.isfile(self.shared_file):
            open(self.shared_file, "w", encoding="utf-8").close()
        ensure_dir(self.downloads_dir)
        ensure_dir(os.path.join(self.downloads_dir, self.current_user))

        # open and tail
        with open(self.shared_file, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)
            # known files
            known_files = list_user_files(self.current_user, self.downloads_dir)

            while self._running:
                line = f.readline()
                if line:
                    clean = line.rstrip("\n")
                    self.new_message.emit(clean)
                    # detect exec
                    try:
                        self.parse_line_for_exec(clean)
                    except Exception:
                        pass
                # check files
                try:
                    new_files, known_files = check_new_files(self.current_user, self.downloads_dir, known_files)
                    for fname in new_files:
                        self.new_file.emit(fname)
                except Exception:
                    pass

                time_ms = int(max(10, self.poll_interval * 1000))
                self.msleep(time_ms)

# -------------------------
# ExecWorker : exécute commandes en arrière-plan
# -------------------------
class ExecWorker(QThread):
    exec_finished = pyqtSignal(str, bool, str)  # cmd, ok, message

    def __init__(self):
        super().__init__()
        self._queue = []
        self._running = True

    def enqueue(self, cmd):
        self._queue.append(cmd)
        if not self.isRunning():
            self.start()

    def run(self):
        while self._running and self._queue:
            cmd = self._queue.pop(0)
            try:
                subprocess.Popen(cmd, shell=True)
                self.exec_finished.emit(cmd, True, "")
            except Exception as e:
                self.exec_finished.emit(cmd, False, str(e))

    def stop(self):
        self._running = False

# -------------------------
# Main Window (UI)
# -------------------------
class ChatWindow(QMainWindow):
    def __init__(self, cfg, username):
        super().__init__()
        self.cfg = cfg
        self.shared_file = cfg["shared_file"]
        self.downloads_dir = cfg["downloads_dir"]
        self.poll_interval = cfg.get("poll_interval", 0.5)
        self.username = username

        self.setWindowTitle("Messagerie PyQt6")
        self.resize(980, 620)

        # central layout: left chat, right panel
        root = QWidget()
        root_layout = QHBoxLayout()
        root.setLayout(root_layout)
        self.setCentralWidget(root)

        # left: chat view + input
        left = QVBoxLayout()
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setPlaceholderText("Aucun message pour le moment")
        left.addWidget(self.chat_view)

        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Tapez votre message...")
        self.input_box.returnPressed.connect(self.on_send_clicked)
        send_btn = QPushButton("Envoyer")
        send_btn.clicked.connect(self.on_send_clicked)
        input_layout.addWidget(self.input_box)
        input_layout.addWidget(send_btn)
        left.addLayout(input_layout)

        # right: functions panel
        right = QVBoxLayout()
        title = QLabel("Fonctions")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(title)

        btn_sendfile = QPushButton("@send (Fichier)")
        btn_sendfile.clicked.connect(self.on_send_file_clicked)
        right.addWidget(btn_sendfile)

        btn_exec = QPushButton("@exec (Commande)")
        btn_exec.clicked.connect(self.on_exec_clicked)
        right.addWidget(btn_exec)

        right.addStretch()

        root_layout.addLayout(left, 4)
        root_layout.addLayout(right, 1)

        # workers
        self.reader = ReaderThread(self.shared_file, self.downloads_dir, self.username, poll_interval=self.poll_interval)
        self.reader.new_message.connect(self.append_message)
        self.reader.exec_request.connect(self.on_exec_request_received)
        self.reader.new_file.connect(self.on_new_file_received)
        self.reader.start()

        self.exec_worker = ExecWorker()
        self.exec_worker.exec_finished.connect(self.on_exec_finished)

        # write joined message
        self.append_message(f"[SYSTEM] {self.username} joined the chat")
        self._write_shared(format_msg(self.username, f"{self.username} joined the chat"))

    def closeEvent(self, event):
        # stop threads and log left
        try:
            if self.reader:
                self.reader.stop()
                self.reader.wait(1000)
        except Exception:
            pass
        try:
            if self.exec_worker:
                self.exec_worker.stop()
        except Exception:
            pass

        self._write_shared(format_msg(self.username, f"{self.username} left the chat"))
        event.accept()

    # ----------------------------------------
    # UI helpers
    # ----------------------------------------
    @pyqtSlot()
    def on_send_clicked(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self._write_shared(format_msg(self.username, text))
        self.input_box.clear()

    @pyqtSlot(str)
    def append_message(self, text):
        self.chat_view.append(text)
        self.chat_view.ensureCursorVisible()

    # ----------------------------------------
    # @send (file) flow
    # ----------------------------------------
    def on_send_file_clicked(self):
        # choose file
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier à envoyer")
        if not path:
            return
        dest, ok = QInputDialog.getText(self, "Destinataire", "Nom du destinataire (username) :")
        if not ok or not dest.strip():
            return
        dest = dest.strip()
        try:
            filename, dest_path = send_file_binary(path, dest, self.downloads_dir)
            # notify in chat
            self._write_shared(format_msg(self.username, f"[FILE] Sent {filename} to {dest}"))
            self.append_message(f"[OK] Fichier envoyé: {filename} -> {dest}")
        except Exception as e:
            self.append_message(f"[ERROR] Envoi fichier: {e}")

    # when a new file appears in Downloads/<user>
    @pyqtSlot(str)
    def on_new_file_received(self, filename):
        self.append_message(f"[FILE] Nouveau fichier reçu : {filename}")

    # ----------------------------------------
    # @exec flow (sending)
    # ----------------------------------------
    def on_exec_clicked(self):
        dest, ok1 = QInputDialog.getText(self, "Destinataire", "Destinataire (username) :")
        if not ok1 or not dest.strip():
            return
        cmd, ok2 = QInputDialog.getText(self, "Commande", "Commande à exécuter :")
        if not ok2 or not cmd.strip():
            return
        dest = dest.strip()
        cmd = cmd.strip()
        self._write_shared(format_msg(self.username, f"@exec {dest} {cmd}"))
        self.append_message(f"[SENT] @exec {dest} {cmd}")

    # ----------------------------------------
    # @exec flow (receiving)
    # ----------------------------------------
    @pyqtSlot(str, str)
    def on_exec_request_received(self, sender, command):
        # show modal question (UI thread) - blocking is fine for modal dialog
        reply = QMessageBox.question(self, "Demande d'exécution",
                                     f"{sender} demande d'exécuter :\n\n{command}\n\nAccepter ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._write_shared(format_msg(self.username, f"[EXEC] Accepted command from {sender}: {command}"))
            # run in worker
            self.exec_worker.enqueue(command)
            self.append_message(f"[EXEC] Accepted and executing: {command}")
        else:
            self._write_shared(format_msg(self.username, f"[EXEC] Refused command from {sender}: {command}"))
            self.append_message(f"[EXEC] Refused: {command} (from {sender})")

    @pyqtSlot(str, bool, str)
    def on_exec_finished(self, cmd, ok, msg):
        if ok:
            self.append_message(f"[EXEC] Execution launched: {cmd}")
        else:
            self.append_message(f"[EXEC] Execution error: {cmd} ({msg})")

    # ----------------------------------------
    # Utility: write to shared file with fsync
    # ----------------------------------------
    def _write_shared(self, content):
        try:
            with open(self.shared_file, "a", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        except Exception as e:
            self.append_message(f"[ERROR] Impossible d'écrire dans le fichier partagé: {e}")


# -------------------------
# Entrypoint
# -------------------------
def main():
    cfg = cfg = load_config(path="C:/Users/Perso/Documents/github/pro/projet_messagerie/lib/chat.json")
    app = QApplication(sys.argv)

    username, ok = QInputDialog.getText(None, "Connexion", "Entrez votre nom d'utilisateur :")
    if not ok or not username.strip():
        return

    username = username.strip()
    win = ChatWindow(cfg, username)
    win.show()
    app.exec()

if __name__ == "__main__":
    main()
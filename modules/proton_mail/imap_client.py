import imaplib

from utils.logging import technical_log


class IMAPClient:
    def __init__(self, config):
        self.config = config
        self.imap = None

    def connect(self):
        if self.imap:
            return self.imap

        try:
            bridge = self.config.get("proton_bridge", {})
            self.imap = imaplib.IMAP4(
                bridge.get("host", "127.0.0.1"),
                bridge.get("imap_port", 1143)
            )
            self.imap.login(
                bridge.get("username"),
                bridge.get("password")
            )
            technical_log("proton-mail", "IMAP connected")
        except Exception as e:
            technical_log("proton-mail", f"IMAP connection failed: {e}")
            self.imap = None

        return self.imap
import time

from imap_tools import MailBox, AND
from loguru import logger


class MailUtils:
    def __init__(self, email: str, imap_pass: str):
        self.email = email
        self.imap_pass = imap_pass

    def get_msg(self, to=None, subject=None, from_=None, seen=None, limit=None, reverse=True, delay=60):
        time.sleep(3)
        with MailBox(self.parse_domain()).login(self.email, self.imap_pass) as mailbox:
            for _ in range(delay // 3):
                try:
                    time.sleep(3)
                    for msg in mailbox.fetch(AND(to=to, subject=subject, from_=from_,
                                                 seen=seen), limit=limit, reverse=reverse):

                        logger.success(f'{self.email} | Successfully received msg')  # : {msg.subject}
                        return {"success": True, "msg": msg.html}
                except Exception as error:
                    logger.error(f'{self.email} | Unexpected error when getting code: {str(error)}')
                # else:
                #     logger.error(f'{self.email} | No message received')
        return {"success": False, "msg": "Didn't find msg"}

    def parse_domain(self):
        domain = self.email.split("@")[-1]

        if "hotmail" in domain or "live" in domain:
            domain = "outlook.com"
        elif "firstmail" in domain:
            domain = "firstmail.ltd"

        return f"imap.{domain}"

import time
from concurrent.futures import ThreadPoolExecutor

from core.utils import shift_file, logger
from core.utils.auto_generate.wallets import generate_random_wallets
from core.utils.file_to_list import file_to_list
from core.magicsquare import MagicSquare

from inputs.config import (
    REFERRAL, THREADS, CUSTOM_DELAY, EMAILS_FILE_PATH, KEYS_FILE_PATH, PROXIES_FILE_PATH, IS_VERIFY_EMAIL, IS_SNAPSHOT
)


class AutoReger:
    def __init__(self):
        self.success = 0
        self.custom_user_delay = None

    @staticmethod
    def get_accounts():
        emails = file_to_list(EMAILS_FILE_PATH)
        keys = file_to_list(KEYS_FILE_PATH)
        proxies = file_to_list(PROXIES_FILE_PATH)

        min_accounts_len = len(emails) or 100

        if not emails and IS_VERIFY_EMAIL:
            logger.info(f"emails.txt is empty!")
            return

        if not keys:
            logger.info(f"keys.txt is empty! Generated random wallets!")
            keys = [wallet[1] for wallet in generate_random_wallets(min_accounts_len)]

        min_accounts_len = len(keys)

        accounts = []

        for i in range(min_accounts_len):
            accounts.append((*(emails[i].split(":")[:2] if len(emails) > i else (None, None)),
                             keys[i],
                             proxies[i] if len(proxies) > i else None))

        return accounts

    @staticmethod
    def remove_account():
        return shift_file(EMAILS_FILE_PATH), shift_file(KEYS_FILE_PATH), shift_file(PROXIES_FILE_PATH)

    def start(self):
        referral_link = REFERRAL

        MagicSquare.referral = referral_link.split('/')[-1]

        threads = THREADS

        self.custom_user_delay = CUSTOM_DELAY

        accounts = AutoReger.get_accounts()

        if accounts is None:
            return

        with ThreadPoolExecutor(max_workers=threads) as executor:
            executor.map(self.register, accounts)

        if self.success:
            logger.success(f"Successfully handled {self.success} accounts :)")
        else:
            logger.warning(f"No accounts handled :(")

    def register(self, account: tuple):
        magic_square = MagicSquare(*account)
        is_ok = False
        logs_file_name = "fail"
        log_msg = "Login successful"

        try:
            time.sleep(self.custom_user_delay)

            if magic_square.login():
                logger.debug(f"Logged in as {account[0]}")
                if IS_VERIFY_EMAIL:
                    if magic_square.fill_details():
                        msg = " | Email verified!"
                        log_msg += msg
                        logger.debug(msg)
                        is_ok = True

                if IS_SNAPSHOT:
                    if magic_square.handle_snapshots():
                        msg = " | Voted on snapshots!"
                        log_msg += msg
                        logger.debug(msg)
                        is_ok = True

                if not IS_VERIFY_EMAIL and not IS_SNAPSHOT:
                    is_ok = True

        except Exception as e:
            logger.error(f"Error {e}")

        AutoReger.remove_account()

        if is_ok:
            logs_file_name = "success"
            self.success += 1
        else:
            log_msg = "Check logs/out.log for more info"

        magic_square.logs(logs_file_name, log_msg)

    @staticmethod
    def is_file_empty(path: str):
        return not open(path).read().strip()

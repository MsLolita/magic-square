import random
import time
from random import choice
from datetime import datetime, timezone

import requests
from fake_useragent import UserAgent  # pip install fake-useragent
from bs4 import BeautifulSoup
from hexbytes import HexBytes

from core.exceptions import NoVerifyMail
from core.utils import str_to_file, logger, CaptchaService
from string import ascii_lowercase, digits


from core.utils import (
    Web3Utils,
    MailUtils,
    Person
)

from inputs.config import (
    MOBILE_PROXY,
    MOBILE_PROXY_CHANGE_IP_LINK
)


class MagicSquare(Web3Utils, MailUtils, Person):
    referral = None

    def __init__(self, email: str, imap_pass: str, key: str, proxy: str = None):
        Person.__init__(self)
        Web3Utils.__init__(self, key=key)
        MailUtils.__init__(self, email, imap_pass)

        self.proxy = MagicSquare.get_proxy(proxy)

        self.headers = {
            'authority': 'magic.store',
            'accept': 'application/json',
            'accept-language': 'uk-UA,uk;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://magic.store',
            'referer': 'https://magic.store/',
            'user-agent': UserAgent().random,
        }

        self.session = requests.Session()

        self.session.headers.update(self.headers)
        self.session.proxies.update({'https': self.proxy, 'http': self.proxy})
        self.session.cookies.update({'referral': MagicSquare.referral})

    @staticmethod
    def get_proxy(proxy: str):
        if MOBILE_PROXY:
            MagicSquare.change_ip()
            proxy = MOBILE_PROXY.replace("https", "http")

        if proxy is not None:
            return f"http://{proxy}"

    @staticmethod
    def change_ip():
        requests.get(MOBILE_PROXY_CHANGE_IP_LINK)

    # def check_ip(self):
    #     print(self.session.get("https://httpbin.org/ip").text)

    def login(self):
        self.session.cookies.update({'MSQ_CONNECTED_WALLET_TYPE': "EVM",
                                     "MSQ_CONNECTED_WALLET_ADDRESS": self.acct.address})
        self.get_authorization_token()
        resp_json = self.connect_wallet()
        logger.debug(f"Login response: {resp_json}")
        return isinstance(resp_json.get("id"), int)

    def get_nonce(self):
        url = 'https://magic.store/api/v2/magicid/nonce'

        headers = self.session.headers
        headers["x-cf-token"] = CaptchaService().get_captcha_token()

        res = self.session.get(url)
        return res.text.strip('"')

    def get_authorization_token(self):
        url = 'https://magic.store/api/v2/magicid/auth/login/wallet'

        msg = (f"magic.store wants you to sign in with your Ethereum account:\n{self.acct.address}\n\n"
               f"Confirm authorization in magic.store with your account\n\nURI: https://magic.store\nVersion: 1\n"
               f"Chain ID: 1\nNonce: {self.get_nonce()}\nIssued At: {self.get_formatted_time()}")

        json_data = {
            'pub_key': self.acct.address.lower(),
            'signature': self.get_signed_code(msg),
            'message': msg,
            'network': 'EVM',
            'wallet': 'EVM',
        }

        res = self.session.post(url, json=json_data)

        return res.json()

    def connect_wallet(self):
        url = 'https://magic.store/api/v2/magicid/user/wallet/connect'

        json_data = {
            'network': 'EVM',
            'pub_key': self.acct.address.lower(),
            'wallet': 'EVM',
            'referredBy': MagicSquare.referral,
        }

        res = self.session.post(url, json=json_data)

        return res.json()

    def fill_details(self):
        self.set_username()
        self.set_name()
        resp_json = self.set_email()
        logger.debug(f"Email response: {resp_json}")
        return isinstance(resp_json.get("id"), int)

    def set_username(self):
        url = "https://magic.store/api/v1/magicid/user"

        json_data = {
            'name': self.username,
        }

        res = self.session.put(url, json=json_data)

        return res.json()

    def set_name(self):
        url = 'https://magic.store/api/v1/magicid/user/additionalInfo'

        json_data = {
            'displayedName': self.first_name,
        }

        res = self.session.put(url, json=json_data)

        return res.json()

    def set_email(self):
        resp_json = self.send_verify_code()
        logger.debug(f"Email setup response: {resp_json}")
        return self.verify_email()

    def send_verify_code(self):
        url = 'https://magic.store/api/v2/magicid/user/email/send-code'

        json_data = {
            'email': self.email,
        }

        res = self.session.post(url, json=json_data)

        return res.json()

    def verify_email(self):
        verify_code = self.get_verify_code()
        return self.approve_email(verify_code)

    def get_verify_code(self):
        result = self.get_msg(from_="hello@magic.store", to=self.email, limit=3)

        if not result["success"]:
            raise NoVerifyMail("Didn't come verify mail!")

        html = result["msg"]
        soup = BeautifulSoup(html, 'lxml')
        a = soup.select_one('strong')
        return a.text

    def approve_email(self, verify_code: str):
        url = "https://magic.store/api/v1/magicid/user/emailCode/verify"

        json_data = {
            'email': self.email,
            'code': int(verify_code),
        }

        response = self.session.post(url, json=json_data)

        return response.json()

    def get_votes_links(self):
        url = 'https://magic.store/api/v2/store/proposals'

        params = {
            'offset': '0',
            'limit': '100',
            'participation': 'NOT_PARTICIPATED',
            'proposal': 'ACTIVE',
        }

        response = self.session.get(url, params=params)

        rows = response.json()["rows"]

        return [f"https://magic.store/app/{row['app_id']}" for row in rows]

    def handle_snapshots(self):
        links = self.get_votes_links()

        if not links:
            logger.info(f"No projects to vote for | {self.email or self.acct.address}")
            return True

        logger.info(f"{self.email or self.acct.address} starting to vote for {len(links)} projects")

        results = []
        for link in links:
            if self.handle_vote(link):
                results.append(link)
            else:
                logger.error(f"Failed to vote for {link} | {self.email or self.acct.address}")

        logger.info(f"Voted for {len(results)}/{len(links)} projects")

        return results

    def handle_vote(self, link: str):
        for _ in range(3):
            try:
                time.sleep(random.uniform(5, 10))
                project_name = link.split("/")[-1]
                resp_json = self.vote(project_name)
                logger.debug(f"Vote response ({project_name}): {resp_json}")

                if resp_json.get("success"):
                    return True
            except Exception as e:
                logger.debug(f"Failed to vote for {link} | {e}")

    def vote(self, project_name: str):
        url = "https://magic.store/api/v2/validation/vote"

        proposal, title = self.get_vote_id(project_name)
        yes_or_no = random.choice([(1, "yes"), (2, "no")])
        message = f'Vote ({yes_or_no[1]}) for {title} at Magic Store: {self.acct.address}'

        signature = self.get_signed_code(message)

        json_data = {
            'vote': yes_or_no[0],
            'proposal': proposal,
            'pubKey': self.acct.address.lower(),
            'network': 'EVM',
            'message': message,
            'signature': signature,
        }

        response = self.session.post(url, json=json_data)

        return response.json()

    def vote_snapshot(self, project_name: str):
        url = 'https://seq.snapshot.org/'

        headers = self.session.headers.copy()
        headers["authority"] = 'seq.snapshot.org'

        timestamp = int(time.time())
        proposal = self.get_vote_id(project_name)
        vote_side = random.randint(1, 2)

        if proposal is None:
            raise ValueError(f"Can't vote for {project_name}")

        message = {
            'space': 'magicappstore.eth',
            'proposal': HexBytes(proposal),
            'choice': vote_side,
            'app': project_name,
            'reason': '',
            'metadata': '{}',
            'from': self.acct.address,
            'timestamp': timestamp,
        }

        domain = {
            'name': 'snapshot',
            'version': '0.1.4',
        }

        msg_type = {
            "Vote": [
                {
                    'name': 'from',
                    'type': 'address',
                },
                {
                    'name': 'space',
                    'type': 'string',
                },
                {
                    'name': 'timestamp',
                    'type': 'uint64',
                },
                {
                    'name': 'proposal',
                    'type': 'bytes32',
                },
                {
                    'name': 'choice',
                    'type': 'uint32',
                },
                {
                    'name': 'reason',
                    'type': 'string',
                },
                {
                    'name': 'app',
                    'type': 'string',
                },
                {
                    'name': 'metadata',
                    'type': 'string',
                },
            ],
        }

        struct_to_sign = {
            "types": {
                "EIP712Domain": [
                    {
                        "name": "name",
                        "type": "string",
                    },
                    {
                        "name": "version",
                        "type": "string",
                    },
                ],
                **msg_type,
            },
            "domain": domain,
            "primaryType": "Vote",
            "message": message,
        }

        signature = self.get_signed_code_struct(struct_to_sign)

        message["proposal"] = proposal

        json_data = {
            'address': self.acct.address,
            'sig': signature,
            'data': {
                "domain": domain,
                'types': {
                    **msg_type
                },
                'message': message,
            },
        }

        response = self.session.post(url, headers=headers, json=json_data)

        return response.json()

    def get_vote_id(self, project_name: str):
        url = 'https://magic.store/api/v1/main/validation/app'

        params = {
            'id': project_name,
            'limit': '30',
            'offset': '0',
        }

        response = self.session.get(url, params=params)

        res = response.json()

        return res["id"], res["title"]

    def claim_daily_bonus(self):
        pass

    def logs(self, file_name: str, msg_result: str = ""):
        acc_id = self.email or self.acct.address

        file_msg = f"{acc_id}|{self.acct.key.hex()}|{self.proxy}"
        str_to_file(f"./logs/{file_name}.txt", file_msg)

        if file_name == "success":
            logger.success(f"{acc_id} | {msg_result}")
        else:
            logger.error(f"{acc_id} | {msg_result}")

    @staticmethod
    def generate_password(k=10):
        return ''.join([choice(ascii_lowercase + digits) for _ in range(k)])

    @staticmethod
    def get_formatted_time():
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

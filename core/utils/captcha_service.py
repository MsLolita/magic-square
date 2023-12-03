import asyncio

from twocaptcha import TwoCaptcha
from anticaptchaofficial.turnstileproxyless import *

from inputs.config import (
    TWO_CAPTCHA_API_KEY,
    ANTICAPTCHA_API_KEY,
    CAPTCHA_PARAMS
)


class CaptchaService:
    def __init__(self):
        self.SERVICE_API_MAP = {
            "2captcha": TWO_CAPTCHA_API_KEY,
            "anticaptcha": ANTICAPTCHA_API_KEY,
        }

        self.captcha_type = CAPTCHA_PARAMS.pop("captcha_type")

    def get_captcha_token(self):
        service, api_key = self._parse_captcha_type()
        return getattr(self, f"bypass_{service}")(api_key)

    def bypass_2captcha(self, api_key):
        solver = TwoCaptcha(api_key)
        result = getattr(solver, self.captcha_type)(**CAPTCHA_PARAMS)

        return result["code"]

    def bypass_anticaptcha(self, api_key):
        solver = globals().get(f"{self.captcha_type}Proxyless")()
        solver.set_key(api_key)
        solver.set_website_url(CAPTCHA_PARAMS["url"])
        solver.set_website_key(CAPTCHA_PARAMS["sitekey"])

        return solver.solve_and_return_solution()

    def _parse_captcha_type(self):
        for service, api_key in self.SERVICE_API_MAP.items():
            if api_key:
                return service, api_key
        raise ValueError("No valid captcha solving service API key found")

    async def get_captcha_token_async(self):
        return await asyncio.to_thread(self.get_captcha_token)

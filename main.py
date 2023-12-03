import ctypes

from core.autoreger import AutoReger
from art import tprint


def bot_info(name: str = ""):
    tprint(name)
    ctypes.windll.kernel32.SetConsoleTitleW(f"{name}")
    print("EnJoYeR's <crypto/> moves: https://t.me/+tdC-PXRzhnczNDli\n")


def main():
    bot_info("Magic Square")
    AutoReger().start()


if __name__ == '__main__':
    main()

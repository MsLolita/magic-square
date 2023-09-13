import random
import string

import names
from random_words import RandomNicknames  # pip install RandomWords


class Person:
    def __init__(self):
        self.username = RandomNicknames().random_nick(gender=random.choice(['f', 'm'])).lower() + \
                        Person.random_string(3) + str(random.randint(1000, 9999))
        self.first_name, self.last_name = names.get_full_name().split(" ")

    @staticmethod
    def random_string(length, chars=string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(length))


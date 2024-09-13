import random
import time
from datetime import datetime
from sys import stderr

from eth_account import Account
from eth_account.messages import encode_defunct
from fake_useragent import UserAgent
from loguru import logger
from requests import get, post
from tqdm import tqdm

choice = "base"  # base | arbitrum
use_proxy = True  # True | False
shuffle_keys = True  # True | False
delay_between_wallets = [20, 40]

message = f"My choice is: {choice.title()}"
base_url = "https://claim.ether.fi/api/s3-preference"

ua = UserAgent()

logger.remove()
logger.add(
    stderr,
    format="<white>{time:HH:mm:ss}</white> | <level>{message}</level>",
)


def load_private_keys(path):
    with open(path) as file:
        keys = [row.strip() for row in file]

    if shuffle_keys:
        random.shuffle(keys)

    return keys


def load_proxies(path):
    with open(path) as file:
        return [f"http://{row.strip()}" for row in file]


def sleep(from_sleep, to_sleep):
    x = random.randint(from_sleep, to_sleep)
    desc = datetime.now().strftime("%H:%M:%S")

    for _ in tqdm(
        range(x), desc=desc, bar_format="{desc} | Sleeping {n_fmt}/{total_fmt}"
    ):
        time.sleep(1)
    print()


def check_ip(proxy, label):
    try:
        proxies = {"http": proxy, "https": proxy} if use_proxy else None
        resp = get("https://httpbin.org/ip", proxies=proxies, timeout=10)
        ip = resp.json()["origin"]
        logger.info(f"{label} Current IP: {ip}")

    except Exception as error:
        logger.error(f"{label} Failed to get IP: {error}")


def generate_headers():
    headers = {
        "user-agent": ua.random,
        "accept-language": "en-US,en;q=0.9",
        "accept": "application/json",
        "referer": "https://claim.ether.fi/season-3",
    }
    return headers


def check_preference(url, address, proxy, label):
    try:
        headers = generate_headers()
        proxies = {"http": proxy, "https": proxy} if use_proxy else None

        resp = get(f"{url}?address={address}", headers=headers, proxies=proxies)
        data = resp.json()

        if data["selection"] is not None:
            logger.debug(
                f"{label} Preference already set to {data['selection'].title()} \n"
            )
            return data["selection"]
        else:
            logger.info(f"{label} Preference is not set...")
            time.sleep(random.randint(5, 15))
            return False

    except Exception as error:
        logger.error(f"{label} Failed to check preference: {error} \n")


def set_preference(url, address, preference, signature, proxy, label):
    try:
        headers = generate_headers()
        payload = {
            "address": address,
            "preference": preference,
            "signature": signature,
        }
        proxies = {"http": proxy, "https": proxy} if use_proxy else None

        resp = post(url, json=payload, headers=headers, proxies=proxies)
        data = resp.json()

        if data.get("success"):
            logger.success(
                f"{label} ETHFI network preference set to {choice.title()} \n"
            )

    except Exception as error:
        logger.error(f"{label} Failed to set preference: {error} \n")


def sign_message(message, private_key):
    message_encoded = encode_defunct(text=message)
    signed_message = Account.sign_message(message_encoded, private_key=private_key)
    return "0x" + signed_message.signature.hex()


if __name__ == "__main__":
    try:
        keys = load_private_keys("keys.txt")
        proxies = load_proxies("proxies.txt")

        total_keys = len(keys)

        if use_proxy == False:
            logger.warning("Not using proxy \n")

        for index, private_key in enumerate(keys, start=1):
            account = Account.from_key(private_key)
            address = account.address
            label = f"[{index}/{total_keys}] {address} |"
            proxy = random.choice(proxies)

            check_ip(proxy, label)
            preference = check_preference(base_url, address, proxy, label)

            if preference:
                continue  # jump to the next wallet

            signature = sign_message(message, private_key)
            set_preference(base_url, address, choice, signature, proxy, label)

            if index < total_keys:
                sleep(*delay_between_wallets)

    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")

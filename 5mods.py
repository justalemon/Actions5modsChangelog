import json
import os
import sys

import requests
from lxml import html

GITHUB_EVENT = os.environ.get("GITHUB_EVENT_NAME", "")
GITHUB_EVENT_DATA = os.environ.get("GITHUB_EVENT_PATH", "")
INPUT_USERNAME = os.environ.get("INPUT_USERNAME", "")
INPUT_PASSWORD = os.environ.get("INPUT_PASSWORD", "")
INPUT_MODTYPE = os.environ.get("INPUT_MODTYPE", "")
INPUT_MODNAME = os.environ.get("INPUT_MODNAME", "")
XPATH_CSRF = "//meta[@name='csrf-token']/@content"
XPATH_MODID = "//div[@id='file']/@data-user-file-id"
TYPES = ["tools", "vehicles", "paintjobs", "weapons", "scripts", "player", "maps", "misc"]
DOMAIN = "https://www.gta5-mods.com"


def checks():
    """
    Checks that all of the required variables are present and valid.
    """
    if GITHUB_EVENT != "release":
        print("This action can only be triggered on Releases.")
        sys.exit(1)

    if not INPUT_USERNAME or INPUT_USERNAME.isspace():
        print("Username is not valid and/or only contains whitespaces.")
        sys.exit(1)
    if not INPUT_PASSWORD or INPUT_PASSWORD.isspace():
        print("Password is not valid and/or only contains whitespaces.")
        sys.exit(1)
    if not INPUT_MODTYPE or INPUT_MODTYPE.isspace() or INPUT_MODTYPE not in TYPES:
        print("Mod Type is not valid and/or only contains whitespaces.")
        sys.exit(1)
    if not INPUT_MODNAME or INPUT_MODNAME.isspace():
        print("Mod Name is not valid and/or only contains whitespaces.")
        sys.exit(1)


def main():
    """
    Sends the changelog message to 5mods.
    """
    # Read the GitHub Event Data for using it later
    with open(GITHUB_EVENT_DATA) as file:
        data = json.load(file)
        print(data)

    # Make a session for storing the cookies
    # (kinda required for 5mods, due to how the site works)
    session = requests.Session()
    session.headers["User-Agent"] = "Fangy (+https://github.com/justalemon/Fangy)"
    # Request the main page, for filling the cookies and fetch the csrf-token
    # (https://laravel.com/docs/8.x/csrf#csrf-x-csrf-token)
    home = session.get(DOMAIN)
    csrf = html.fromstring(home.text).xpath(XPATH_CSRF)
    # If there is no csrf-token or is invalid, print a message and exit
    if not csrf or not csrf[0]:
        print("No csrf-token meta tag was found!")
        sys.exit(2)
    # If there is, add it to the session tokens
    session.headers["X-CSRF-Token"] = csrf[0]

    # Now, go ahead and log into 5mods
    # The session should handle everything
    login_data = {
        "utf8": "✓",
        "user[username]": INPUT_USERNAME,
        "user[password]": INPUT_PASSWORD,
        "user[remember_me]": 1,
        "commit": "Log In"
    }
    login = session.post(f"{DOMAIN}/login", login_data)
    # If the code was other than 200, print the message and return
    if login.status_code != 200:
        print("Unable to Log In: " + login.json()["errors"])
        sys.exit(3)

    # Now, time to fetch the Numeric ID of the mod (required for posting comments)
    # This is present on the body on the file id as data-user-file-id
    mod = session.get(f"{DOMAIN}/{INPUT_MODTYPE}/{INPUT_MODNAME}")
    if mod.status_code != 200:
        print(f"Unable to fetch the Mod Page: Code {mod.status_code}")
        sys.exit(4)
    rawmodid = html.fromstring(mod.text).xpath(XPATH_MODID)
    if not rawmodid:
        print(f"Unable to get the Mod ID from the Mod Page")
        sys.exit(5)
    modid = rawmodid[0]


if __name__ == "__main__":
    checks()
    main()

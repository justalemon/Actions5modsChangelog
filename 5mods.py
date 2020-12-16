import os
import sys

import requests
from lxml import html

USERNAME = os.environ.get("INPUT_USERNAME")
PASSWORD = os.environ.get("INPUT_PASSWORD")
CSRF = "//meta[@name='csrf-token']/@content"
DOMAIN = "https://www.gta5-mods.com"


def main():
    """
    Sends the changelog message to 5mods.
    """
    # Make a session for storing the cookies
    # (kinda required for 5mods, due to how the site works)
    session = requests.Session()
    session.headers["User-Agent"] = "Fangy (+https://github.com/justalemon/Fangy)"
    # Request the main page, for filling the cookies and fetch the csrf-token
    # (https://laravel.com/docs/8.x/csrf#csrf-x-csrf-token)
    home = session.get(DOMAIN)
    csrf = html.fromstring(home.text).xpath(CSRF)
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
        "user[username]": USERNAME,
        "user[password]": PASSWORD,
        "user[remember_me]": 1,
        "commit": "Log In"
    }
    login = session.post(f"{DOMAIN}/login", login_data)
    # If the code was other than 200, print the message and return
    if login.status_code != 200:
        json = login.json()
        print("Unable to Log In: " + json["errors"])
        sys.exit(3)


if __name__ == "__main__":
    main()

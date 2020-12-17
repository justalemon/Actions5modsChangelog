import json
import os
import re
import sys

import requests
from lxml import html

GITHUB_EVENT = os.environ.get("GITHUB_EVENT_NAME", "")
GITHUB_EVENT_DATA = os.environ.get("GITHUB_EVENT_PATH", "")
GITHUB_REF = os.environ.get("GITHUB_REF", "")  # Tag
INPUT_USERNAME = os.environ.get("INPUT_USERNAME", "")
INPUT_PASSWORD = os.environ.get("INPUT_PASSWORD", "")
INPUT_MODTYPE = os.environ.get("INPUT_MODTYPE", "")
INPUT_MODNAME = os.environ.get("INPUT_MODNAME", "")
INPUT_PIN = os.environ.get("INPUT_PIN", "true").lower() == "true"
INPUT_FEATURE = os.environ.get("INPUT_FEATURE", "true").lower() == "true"
XPATH_CSRF = "//meta[@name='csrf-token']/@content"
XPATH_MODID = "//div[@id='file']/@data-user-file-id"
REGEX_COMMENTID = "data-comment-id=\\\\\"([0-9]*)\\\\\""
TYPES = ["tools", "vehicles", "paintjobs", "weapons", "scripts", "player", "maps", "misc"]
DOMAIN = "https://www.gta5-mods.com"


def update_csrf(session: requests.Session, response: requests.Response = None):
    """
    Updates the X-CSRF-Token header for the Session.
    """
    # If there is no response, request the main mod page
    if response is None:
        response = session.get(f"{DOMAIN}/{INPUT_MODTYPE}/{INPUT_MODNAME}")

    # Make sure that the response was code 200
    if response.status_code != 200:
        print(f"Unable to update CSRF for URL {response.url}")
        sys.exit(2)

    # Parse the HTML and get the CSRF from meta
    csrf = html.fromstring(response.text).xpath(XPATH_CSRF)
    # If there is no csrf-token or is invalid, print a message and exit
    if not csrf or not csrf[0]:
        print(f"No csrf-token meta tag was found! (For URL {response.url})")
        sys.exit(2)
    # If there is, add it to the session tokens
    session.headers["X-CSRF-Token"] = csrf[0]


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

    # Make a session for storing the cookies
    # (kinda required for 5mods, due to how the site works)
    session = requests.Session()
    session.headers["User-Agent"] = "Fangy (+https://github.com/justalemon/Fangy)"
    # Request the main page, for filling the cookies and fetch the csrf-token
    # (https://laravel.com/docs/8.x/csrf#csrf-x-csrf-token)
    update_csrf(session, session.get(DOMAIN))

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

    # Time to update the CSRF, again
    update_csrf(session, mod)

    # Now, is time to send the message to the 5mods page
    message = data["release"]["body"]
    cdata = {
        "utf8": "✓",
        "user_file[id]": modid,
        "comment[comment]": f"{GITHUB_REF} Changelog: \n\n{message}",
        "commit": "Post Comment"
    }
    comment = session.post(f"{DOMAIN}/api/comments", cdata)
    if comment.status_code != 200:
        print(f"Unable to Post the comment to 5mods: Code {comment.status_code}")
        sys.exit(6)

    # The Comment ID is sent as part of the response of the request above
    # Because the site was made by someone in drugs, is JavaScript meant to be executed on the client browser
    # So we need to use a RegEx to find the Comment ID in the entire JS Code
    regex = re.search(REGEX_COMMENTID, comment.text)
    commentid = int(regex.group(1))

    # Now that the comment has been posted, time to pin and/or feature
    # Let's start with the pin (required for featured)
    if INPUT_PIN or INPUT_FEATURE:
        data = {
            "comment": {
                "id": commentid
            }
        }
        update_csrf(session)
        pin = session.patch(f"{DOMAIN}/api/comments/pin", data,
                            headers={"Content-Type": "application/json"})
        print(session.cookies)
        if pin.status_code != 200:
            print(f"Unable to Pin Comment {commentid}: Code {pin.status_code} ({pin.text})")
            sys.exit(7)
    if INPUT_FEATURE:
        data = {
            "comment": {
                "id": commentid,
                "featured": True
            }
        }
        update_csrf(session)
        featured = session.patch(f"{DOMAIN}/api/comments/feature", data,
                                 headers={"Content-Type": "application/json"})
        if featured.status_code != 200:
            print(f"Unable to Feature Comment {commentid}: Code {featured.status_code}")
            sys.exit(8)

    # If we got here, the nightmares have ended
    print(f"Done! (Comment ID: {commentid})")


if __name__ == "__main__":
    checks()
    main()

#!/usr/bin/env python3

import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

LINKS = [
    "https://ee.kobotoolbox.org/single/lkdC1f9S",  # VS / SEE
    "https://ee.kobotoolbox.org/single/9MhTiLJL",  # SEE / VS
]
PORT = 8533

index = 0
existing_mappings = {}


class RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global index
        print("Handling request...")
        # We want to consistently associate users with their evaulation variant.
        cookie = SimpleCookie(self.headers.get("Cookie"))
        user_id = None
        if "user_id" in cookie:
            user_id = cookie["user_id"].value
        else:
            user_id = uuid.uuid4().hex

        if user_id not in existing_mappings:
            # Try three times to get existing results for survey.
            for i in range(3):
                try:
                    print("Requesting results...")
                    r = requests.get(
                        "https://kf.kobotoolbox.org/api/v2/assets.json",
                        headers={"Authorization": "Token [REDACTED]"},
                        timeout=5,
                    )
                    print("Got results.")
                    r.raise_for_status()
                    info = r.json()
                    vs = next(
                        x["deployment__submission_count"]
                        for x in info["results"]
                        if x["name"].startswith("VSCode / SEE")
                    )
                    # Minus two because those are from the pilot study.
                    see = (
                        next(
                            x["deployment__submission_count"]
                            for x in info["results"]
                            if x["name"].startswith("SEE / VSCode")
                        )
                        - 2
                    )

                    print(
                        f"We have {vs} VS/SEE submissions, and {see} SEE/VS submissions"
                    )

                    # Then, redirect so that we get an even submission count:
                    if see <= vs:
                        existing_mappings[user_id] = LINKS[1]
                    else:
                        existing_mappings[user_id] = LINKS[0]

                    break
                except requests.RequestException as e:
                    print(f"Try #{i}: request exception occurred ({e})")
            else:
                # Use alternating method instead.
                existing_mappings[user_id] = LINKS[index]
                index = (index + 1) % len(LINKS)

        chosen_link = existing_mappings[user_id]

        self.send_response(303)
        self.send_header("Location", chosen_link)

        # Set cookie to remember existing evaluation association.
        cookie = SimpleCookie()
        cookie["user_id"] = user_id
        cookie["user_id"]["max-age"] = 2592000  # 30 days
        self.send_header("Set-Cookie", cookie["user_id"].OutputString())
        self.end_headers()

    def get_cookie_link(self):
        global index


def run_server():
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, RedirectHandler)
    print(f"Running on port {PORT}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()

import requests

# First, verify what pages your token has access to
def get_pages(user_token):
    r = requests.get(
        "https://graph.facebook.com/v19.0/me/accounts",
        params={"access_token": user_token}
    )
    return r.json()  # lists all pages + their page-level tokens

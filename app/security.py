"""CSRF protection: every POST form must send back the token stored in the session.

This stops another website from submitting forms (for example, deleting a
product) using the visitor's browser.
"""
import hmac
import secrets

from flask import abort, request, session

TOKEN_FIELD = "csrf_token"


def generate_csrf_token():
    """Return the session's token, creating one on first use."""
    if TOKEN_FIELD not in session:
        session[TOKEN_FIELD] = secrets.token_urlsafe(32)
    return session[TOKEN_FIELD]


def check_csrf_token():
    if request.method != "POST":
        return
    expected = session.get(TOKEN_FIELD)
    sent = request.form.get(TOKEN_FIELD, "")
    if not expected or not hmac.compare_digest(sent, expected):
        abort(
            400,
            description=(
                "The form could not be submitted because its security token is "
                "missing or has expired. Go back, reload the page and try again."
            ),
        )


def init_app(app):
    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    app.before_request(check_csrf_token)

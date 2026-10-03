Changelog
=========

* v0.11.0

  - Use ``state`` to identify the user on the setup flow instead of the
    session cookie. The state carries (and signs) the ToxicBuild user id.
  - GitLab: bind the oauth ``state`` to the user id and use it to resolve
    the user, dropping the cookie-based lookup.
  - GitHub: also send the signed ``state`` in the import url.
  - Requires ``toxiccore>=0.14.0`` (``create_validation_string`` /
    ``validate_string`` now support carrying data).

* v0.10.7

  - await ensure_indexes.

* v0.10.6

  - Update mongomotor

* v0.10.5

  - Replace ``pkg_resources`` (removed from the stdlib venvs on python 3.12+)
    with ``importlib.resources`` so ``create`` works on a fresh virtualenv


* v0.10.4

  - Refactor on tests and update deps

* v0.10.3

  - Update toxiccore

* V0.10.2

  - Fix deps

* V0.10.1

  - Fix packaging

* v0.10.0

  - First version on its own repo outside toxicuild

from __future__ import annotations

import keyring
from keyring.errors import KeyringError, PasswordDeleteError


class VaultError(RuntimeError):
    pass


def set_secret(service: str, key: str, value: str) -> None:
    try:
        keyring.set_password(service, key, value)
    except KeyringError as exc:
        raise VaultError(str(exc)) from exc


def get_secret(service: str, key: str) -> str:
    try:
        secret = keyring.get_password(service, key)
    except KeyringError as exc:
        raise VaultError(str(exc)) from exc

    if not secret:
        raise VaultError(f"No secret found for key '{key}' in service '{service}'")
    return secret


def has_secret(service: str, key: str) -> bool:
    try:
        secret = keyring.get_password(service, key)
    except KeyringError as exc:
        raise VaultError(str(exc)) from exc
    return bool(secret)


def delete_secret(service: str, key: str) -> bool:
    try:
        keyring.delete_password(service, key)
    except PasswordDeleteError:
        return False
    except KeyringError as exc:
        raise VaultError(str(exc)) from exc
    return True

# services/inter_api.py

import os
from typing import Any

import requests


class InterAPI:
    def __init__(self):
        self.client_id = os.getenv("INTER_CLIENT_ID")
        self.client_secret = os.getenv("INTER_CLIENT_SECRET")
        self.cert_path = os.getenv("INTER_CERT_PATH")
        self.key_path = os.getenv("INTER_KEY_PATH")
        self.base_url = "https://cdpj.partners.bancointer.com.br"
        self.token = self._get_token()

    def _get_token(self) -> str:
        request_body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "pix.read",
            "grant_type": "client_credentials",
        }

        response = requests.post(
            f"{self.base_url}/oauth/v2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            cert=(self.cert_path, self.key_path),
            data=request_body,
        )
        response.raise_for_status()
        return response.json().get("access_token")

    def get_pix_details(self, e2e_id: str, conta_corrente: str) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "x-conta-corrente": conta_corrente,
            "Content-Type": "Application/json",
        }

        response = requests.get(
            f"{self.base_url}/pix/v2/pix/{e2e_id}",
            headers=headers,
            cert=(self.cert_path, self.key_path),
        )
        response.raise_for_status()
        return response.json()

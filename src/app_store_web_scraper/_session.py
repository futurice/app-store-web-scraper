from __future__ import annotations
from typing import Any
from urllib.parse import urljoin

import urllib3

from .__about__ import __version__
from ._errors import AppNotFound, AppStoreError


class AppStoreSession:
    """
    An App Store session is a pool of HTTP connections to the App Store.
    When scraping multiple App Store entries, using a shared session
    improves performance and resource usage as the same set of HTTP
    connections is reused across requests.
    """

    _web_base_url = "https://apps.apple.com"
    _api_base_url = "https://amp-api-edge.apps.apple.com"
    _user_agent = f"app-store-web-scraper/{__version__}"

    def __init__(
        self,
        retries: int = 5,
        retries_backoff_factor: float = 3,
        retries_backoff_jitter: float = 0,
        retries_backoff_max: float = 60,
    ):
        self._http = urllib3.PoolManager(
            retries=urllib3.Retry(
                total=retries,
                backoff_factor=retries_backoff_factor,
                backoff_jitter=retries_backoff_jitter,
                backoff_max=retries_backoff_max,
                status_forcelist=set([429, 503]),
            )
        )

    def _get_app_page(self, app_id: str | int, country: str) -> str:
        url = urljoin(self._web_base_url, f"/{country}/app/_/id{app_id}")

        response = self._http.request(
            "GET",
            url,
            headers={
                "Origin": self._web_base_url,
                "User-Agent": self._user_agent,
            },
        )

        if response.status == 404:
            raise AppNotFound(app_id, country)
        elif response.status >= 400:
            raise AppStoreError(
                f"Fetching App Store page failed with status {response.status} ({url})"
            )

        return response.data.decode()

    def _get_api_resource(
        self,
        url: str,
        *,
        access_token: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        full_url = urljoin(self._api_base_url, url)

        response = self._http.request(
            "GET",
            full_url,
            fields=params,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Origin": self._web_base_url,
                "User-Agent": self._user_agent,
            },
        )

        if response.status >= 400:
            raise AppStoreError(
                f"App Store API request failed with status {response.status} (GET {full_url})"
            )

        return response.json()

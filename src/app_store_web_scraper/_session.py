from __future__ import annotations

import random
import time
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

    .. code-block :: python

        from app_store_web_scraper import AppStoreEntry, AppStoreSession

        session = AppStoreSession()
        pages = AppStoreEntry(app_id=361309726, country="us", session=session)
        numbers = AppStoreEntry(app_id=361304891, country="us", session=session)

    :param delay:
        The number of seconds to sleep between requests, to reduce the
        probability of hitting API rate limits.

    :param delay_jitter:
        If > 0, randomly add or substract up to this amount of seconds to each
        delay between requests. Ignored if ``delay == 0``.

    :param retries:
        How often to retry a failed request to the App Store API. Before each
        request, the session sleeps for an exponentially growing amount of
        time (backoff).

    :param retries_backoff_factor:
        The backoff time for each retry (``2 ** {number of previous
        replies}`` seconds) is multiplied with this number. For instance, if
        the factor is 0.1, then the sequence of backoff times are 0.1, 0.2,
        0.4, etc.

    :param retries_backoff_jitter:
        If > 0, randomly add or subtract up to this amount of seconds to each
        retry backoff time.
    """

    _web_base_url = "https://apps.apple.com"
    _api_base_url = "https://amp-api-edge.apps.apple.com"
    _user_agent = f"app-store-web-scraper/{__version__}"

    def __init__(
        self,
        delay: float = 0.2,
        delay_jitter: float = 0.05,
        retries: int = 4,
        retries_backoff_factor: float = 2,
        retries_backoff_jitter: float = 0,
        retries_backoff_max: float = 60,
    ):
        self._delay = delay
        self._delay_jitter = delay_jitter

        self._http = urllib3.PoolManager(
            retries=urllib3.Retry(
                total=retries,
                backoff_factor=retries_backoff_factor,
                backoff_jitter=retries_backoff_jitter,
                backoff_max=retries_backoff_max,
                status_forcelist=set([429, 503]),
            )
        )

        self._made_first_request = False

    def _get_app_page(self, app_id: str | int, country: str) -> str:
        self._apply_delay()
        url = urljoin(self._web_base_url, f"/{country}/app/_/id{app_id}")

        response = self._http.request(
            "GET",
            url,
            headers={
                "Origin": self._web_base_url,
                "User-Agent": self._user_agent,
            },
        )

        self._made_first_request = True

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
        self._apply_delay()
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

        self._made_first_request = True

        if response.status >= 400:
            raise AppStoreError(
                f"App Store API request failed with status {response.status} (GET {full_url})"
            )

        return response.json()

    def _apply_delay(self):
        if self._delay > 0 and self._made_first_request:
            jitter = random.uniform(0, self._delay_jitter)
            time.sleep(self._delay + jitter)

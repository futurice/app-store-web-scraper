from __future__ import annotations

import random
import time
from urllib.parse import urljoin

import urllib3

from .__about__ import __version__
from ._errors import AppStoreError


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

    _base_url = "https://itunes.apple.com"

    def __init__(
        self,
        delay: float = 0,
        delay_jitter: float = 0,
        retries: int = 5,
        retries_backoff_factor: float = 5,
        retries_backoff_jitter: float = 0,
        retries_backoff_max: float = 60,
    ):
        self._delay = delay
        self._delay_jitter = delay_jitter
        self._made_first_request = False
        self._http = urllib3.PoolManager(
            headers={"User-Agent": f"app-store-web-scraper/{__version__}"},
            retries=urllib3.Retry(
                total=retries,
                backoff_factor=retries_backoff_factor,
                backoff_jitter=retries_backoff_jitter,
                backoff_max=retries_backoff_max,
                status_forcelist=set([429, 503]),
            ),
        )

    def _get(self, path: str) -> dict:
        if not path.startswith("/"):
            raise ValueError("Path must not be relative or a full URL")

        if self._delay > 0 and self._made_first_request:
            jitter = random.uniform(0, self._delay_jitter)
            time.sleep(self._delay + jitter)

        url = urljoin(self._base_url, path)
        response = self._http.request("GET", url)

        if response.status >= 400:
            message = f"iTunes API request failed with status {response.status}"
            raise AppStoreError(message)

        self._made_first_request = True
        return response.json()

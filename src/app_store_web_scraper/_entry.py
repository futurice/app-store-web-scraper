from __future__ import annotations
import json
import re
import urllib.parse
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from app_store_web_scraper._session import AppStoreError, AppStoreSession
from app_store_web_scraper._utils import fromisoformat_utc


@dataclass
class AppDeveloperResponse:
    """
    An app developer's response to an app review.
    """

    id: int
    body: str
    modified: datetime


@dataclass
class AppReview:
    """
    A user review fetched from the App Store.
    """

    id: int
    date: datetime
    user_name: str
    title: str
    review: str
    rating: int
    is_edited: bool
    developer_response: AppDeveloperResponse | None


_APP_STORE_CONFIG_TAG_PATTERN = re.compile(
    r'<meta name="web-experience-app/config/environment" content="(.+?)">',
)

_REVIEWS_PAGE_SIZE = 20


class AppStoreEntry:
    """
    Represents an app in the app store.

    :param app_id:
        ID of the app in the App Store. It can be found in the last path
        segment of the app's App Store URL (remove the "id" prefix).

    :param country:
        Two-letter ISO code of the country where the app should be looked up.
        Both lowercase ("de") and uppercase ("FI") codes are accepted. The
        :meth:`reviews` method will only return reviews from users of that
        country.

    :param session:
        The :class:`AppStoreSession` to use for communicating with the App
        Store. If not specified, a new session is created internally. Use
        this option to share the same session between entries to increase
        efficiency (by using a shared HTTP connection pool) or to pass a
        session with custom configuration parameters.
    """

    def __init__(
        self,
        app_id: str | int,
        country: str,
        *,
        session: AppStoreSession | None = None,
    ):
        self.app_id = int(app_id)
        self.country = country.lower()
        self._session = session or AppStoreSession()

        page = self._session._get_app_page(app_id, country)
        self._api_access_token = self._extract_api_access_token(page)

    def reviews(self, limit: int = 0) -> Iterator[AppReview]:
        """
        Return an iterator that fetches app reviews from the App Store.

        As the list of reviews is paginated, iterating over all reviews
        triggers an additional HTTP request to the App Store's backend whenever
        a new page needs to be fetched. For this reason, it is possible that
        the iterator raises an error even after some reviews were already
        returned.

        Note that only reviews from the App Store entry's country are returned.
        Also, the App Store's API only returns a subset of all reviews ever
        given to the app, so it is normal that the numer of retrieved reviews
        does not match the review count on the App Store page.

        :param limit:
            The maximum number of reviews to return.

        :return:
            An iterator that lazily fetches the app's reviews.
        """
        path = f"/v1/catalog/{self.country}/apps/{self.app_id}/reviews"

        params = {
            "platform": "web",
            "additionalPlatforms": "appletv,ipad,iphone,mac",
            "sort": "-date",
            "limit": (
                str(min(limit, _REVIEWS_PAGE_SIZE))
                if limit > 0
                else str(_REVIEWS_PAGE_SIZE)
            ),
        }

        query_string = urllib.parse.urlencode(params)
        url = f"{path}?{query_string}"
        review_count = 0

        while url:
            reviews = self._session._get_api_resource(
                url,
                access_token=self._api_access_token,
            )

            for item in reviews["data"]:
                yield self._parse_app_review(item)
                review_count += 1
                if limit > 0 and review_count == limit:
                    return

            # The "next" URL returned by the API is unfortunately not
            # complete: it adds an appropriate `offset` query parameter
            # to the previous URL, but drops all other parameters. We
            # need to re-add them manually as otherwise we'd get a
            # 400 response.
            url = reviews.get("next")
            if url:
                url = f"{url}&{query_string}"

    def _extract_api_access_token(self, page_html: str) -> str:
        if match := re.search(_APP_STORE_CONFIG_TAG_PATTERN, page_html):
            config = json.loads(urllib.parse.unquote(match[1]))
            return config["MEDIA_API"]["token"]
        raise AppStoreError("No API token found on app store page")

    def _parse_app_review(self, item: dict) -> AppReview:
        review_id = item["id"]
        attributes = item["attributes"]
        dev_response = attributes.get("developerResponse")

        return AppReview(
            id=review_id,
            date=fromisoformat_utc(attributes["date"]),
            user_name=attributes["userName"],
            title=attributes["title"],
            review=attributes["review"],
            rating=attributes["rating"],
            is_edited=attributes["isEdited"],
            developer_response=(
                AppDeveloperResponse(
                    id=dev_response["id"],
                    body=dev_response["body"],
                    modified=fromisoformat_utc(dev_response["modified"]),
                )
                if dev_response
                else None
            ),
        )

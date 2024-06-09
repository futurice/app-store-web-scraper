from __future__ import annotations
import json
import re
import urllib.parse
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from app_store_web_scraper._session import AppStoreError, AppStoreSession


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


class AppStoreEntry:
    """
    Represents an app in the app store.
    """

    def __init__(
        self,
        app_id: str | int,
        country: str,
        *,
        session: AppStoreSession | None = None,
    ):
        self.app_id = app_id
        self.country = country
        self._session = session or AppStoreSession()

        page = self._session._get_app_page(app_id, country)
        self._api_access_token = self._extract_api_access_token(page)

    def reviews(self, limit: int = 0) -> Iterator[AppReview]:
        """
        Fetch app reviews from the App Store and return them as an iterator.

        As the list of reviews is paginated, iterating over all reviews
        triggers an additional HTTP request to the App Store's backend whenever
        a new page needs to be fetched. For this reason, it is possible that
        the iterator raises an error even after some reviews were already
        returned.
        """
        path = f"/v1/catalog/{self.country}/apps/{self.app_id}/reviews"

        params = {
            "platform": "web",
            "additionalPlatforms": "appletv,ipad,iphone,mac",
        }

        if limit > 0:
            params["limit"] = str(limit)

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
            date=datetime.fromisoformat(attributes["date"]),
            user_name=attributes["userName"],
            title=attributes["title"],
            review=attributes["review"],
            rating=attributes["rating"],
            is_edited=attributes["isEdited"],
            developer_response=(
                AppDeveloperResponse(
                    id=dev_response["id"],
                    body=dev_response["body"],
                    modified=datetime.fromisoformat(dev_response["modified"]),
                )
                if dev_response
                else None
            ),
        )

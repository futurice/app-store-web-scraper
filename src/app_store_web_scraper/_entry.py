from __future__ import annotations
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from app_store_web_scraper._errors import AppNotFound
from app_store_web_scraper._session import AppStoreSession
from app_store_web_scraper._utils import fromisoformat_utc


@dataclass
class AppDeveloperResponse:
    """
    An app developer's response to an app review.
    """

    id: int
    body: str
    modified: datetime


@dataclass(frozen=True)
class AppReview:
    """
    A user review fetched from the App Store.
    """

    id: int
    date: datetime
    user_name: str
    title: str
    content: str
    rating: int
    app_version: str

    @property
    def review(self) -> str:
        """
        An alias for ``content``, provided for backwards compatibility.
        """
        return self.content


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

    MAX_REVIEWS_LIMIT = 500
    """
    The maximum number of app reviews that can be retrieved for an App Store
    entry. (This limit is imposed by the iTunes Store RSS API.)

    NOTE: The limit is per country, so for apps available in multiple countries,
    it is possible to create one ``AppStoreEntry`` per country and retrieve a
    total maximum of ``MAX_REVIEWS_LIMIT * NUMBER_OF_COUNTRIES`` reviews.
    """

    _REVIEWS_FEED_PAGE_LIMIT = 10
    """
    The maximum amount of pages that an iTunes Store RSS reviews feed returns.
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

    def reviews(self, limit: int = MAX_REVIEWS_LIMIT) -> Iterator[AppReview]:
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
        if limit <= 0:
            raise ValueError("limit must be a positive number")

        count = 0

        for page in range(1, self._REVIEWS_FEED_PAGE_LIMIT + 1):
            path = f"/{self.country}/rss/customerreviews/page={page}/id={self.app_id}/sortby=mostrecent/json"
            data = self._session._get_itunes_rss_json(path)
            feed = data["feed"]

            app_exists = False
            for link in feed["link"]:
                if link["attributes"]["rel"] == "self":
                    app_exists = True

            if not app_exists:
                raise AppNotFound(self.app_id, self.country)

            if "entry" not in feed:
                # There are no more reviews to retrieve
                return

            for entry in feed["entry"]:
                yield self._parse_review_entry(entry)
                count += 1
                if count == limit:
                    return

    def _parse_app_review(self, item: dict) -> AppReview:
        attributes = item["attributes"]
        return AppReview(
            id=item["id"],
            date=fromisoformat_utc(attributes["date"]),
            user_name=attributes["userName"],
            title=attributes["title"],
            content=attributes["review"],
            rating=attributes["rating"],
            app_version="",
        )

    def _parse_review_entry(self, entry: dict) -> AppReview:
        return AppReview(
            id=int(entry["id"]["label"]),
            date=fromisoformat_utc(entry["updated"]["label"]),
            user_name=entry["author"]["name"]["label"],
            title=entry["title"]["label"],
            content=entry["content"]["label"],
            rating=int(entry["im:rating"]["label"]),
            app_version=entry["im:version"]["label"],
        )

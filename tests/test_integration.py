"""
Tests the library as a whole against mocks of Apple's store APIs.
"""

from __future__ import annotations
from datetime import timezone

import pytest
from app_store_web_scraper import AppNotFound, AppReview, AppStoreEntry, AppStoreSession
from faker import Faker
from pytest_httpserver import HTTPServer

# --- Fixtures


APP_ID = "123456789"
COUNTRY = "de"


@pytest.fixture
def session(httpserver: HTTPServer) -> AppStoreSession:
    session = AppStoreSession()
    session._base_url = httpserver.url_for("")
    return session


# --- Helpers


def fake_app_review(faker: Faker):
    return AppReview(
        id=faker.unique.random_int(min=0, max=2**32),
        date=faker.past_datetime(tzinfo=timezone.utc),
        user_name=faker.user_name(),
        title=" ".join(faker.words(3)),
        content=" ".join(faker.sentences(2)),
        rating=faker.random_int(min=1, max=5),
        app_version="1.0.0",
    )


def rss_reviews_feed(reviews: list[AppReview]):
    return {
        "feed": {
            "link": [
                {
                    "attributes": {
                        "rel": "self",
                        "href": "https://mzstoreservices-int-st.itunes.apple.com/...",
                    }
                }
            ],
            "entry": [
                {
                    "id": {
                        "label": str(review.id),
                    },
                    "author": {
                        "name": {
                            "label": review.user_name,
                        },
                    },
                    "title": {
                        "label": review.title,
                    },
                    "content": {
                        "label": review.content,
                    },
                    "im:rating": {
                        "label": str(review.rating),
                    },
                    "im:version": {
                        "label": str(review.app_version),
                    },
                    "updated": {
                        "label": review.date.isoformat().replace("+00:00", "Z"),
                    },
                }
                for review in reviews
            ],
        }
    }


def empty_rss_reviews_feed():
    return {
        "feed": {
            "link": [
                {
                    "attributes": {
                        "rel": "self",
                        "href": "https://mzstoreservices-int-st.itunes.apple.com/...",
                    }
                }
            ],
        },
        # No "entry" attribute
    }


def app_not_found_rss_reviews_feed():
    return {
        "feed": {
            "link": [
                # No "self" link
            ],
        },
        # No "entry" attribute
    }


def mock_rss_reviews_feed(httpserver: HTTPServer, *, page: int, feed: dict):
    httpserver.expect_request(
        f"/{COUNTRY}/rss/customerreviews/page={page}/id={APP_ID}/sortby=mostrecent/json"
    ).respond_with_json(feed)


# --- Tests


class TestAppReviews:
    """
    Tests for ``AppStoreEntry.reviews``.
    """

    def test_single_page_feed(
        self,
        httpserver: HTTPServer,
        faker: Faker,
        session: AppStoreSession,
    ):
        reviews = [fake_app_review(faker) for _ in range(10)]
        mock_rss_reviews_feed(httpserver, page=1, feed=rss_reviews_feed(reviews))
        mock_rss_reviews_feed(httpserver, page=2, feed=empty_rss_reviews_feed())

        app = AppStoreEntry(APP_ID, COUNTRY, session=session)
        retrieved_reviews = list(app.reviews())

        assert retrieved_reviews == reviews

    def test_multi_page_feed(
        self,
        httpserver: HTTPServer,
        faker: Faker,
        session: AppStoreSession,
    ):
        reviews1 = [fake_app_review(faker) for _ in range(50)]
        reviews2 = [fake_app_review(faker) for _ in range(10)]
        mock_rss_reviews_feed(httpserver, page=1, feed=rss_reviews_feed(reviews1))
        mock_rss_reviews_feed(httpserver, page=2, feed=rss_reviews_feed(reviews2))
        mock_rss_reviews_feed(httpserver, page=3, feed=empty_rss_reviews_feed())

        app = AppStoreEntry(APP_ID, COUNTRY, session=session)
        retrieved_reviews = list(app.reviews())

        assert retrieved_reviews == reviews1 + reviews2

    def test_empty_feed(
        self,
        httpserver: HTTPServer,
        faker: Faker,
        session: AppStoreSession,
    ):
        mock_rss_reviews_feed(
            httpserver,
            page=1,
            feed=empty_rss_reviews_feed(),
        )

        app = AppStoreEntry(APP_ID, COUNTRY, session=session)
        retrieved_reviews = list(app.reviews())

        assert retrieved_reviews == []

    def test_app_not_found(
        self,
        httpserver: HTTPServer,
        session: AppStoreSession,
    ):
        mock_rss_reviews_feed(
            httpserver,
            page=1,
            feed=app_not_found_rss_reviews_feed(),
        )

        app = AppStoreEntry(APP_ID, COUNTRY, session=session)

        with pytest.raises(AppNotFound):
            list(app.reviews())

# 🍏🔍 App Store Web Scraper

`app-store-web-scraper` is a Python package for extracting reviews for iOS,
iPadOS, macOS and tvOS apps from the web version of Apple's App Store.

> __Note:__ Whenever possible, prefer using Apple's [App Store Connect
> API][connect], which provides the full set of customer review data for your
> apps and is more reliable.

* [Installation](#installation)
* [Basic Usage](#basic-usage)
    * [App IDs](#app-ids)
    * [App Store Entries](#app-store-entries)
    * [App Reviews](#app-reviews)
* [Advanced Usage](#advanced-usage)
    * [Sessions](#sessions)
* [How It Works](#how-it-works)
* [License](#license)
* [Acknowledgements](#acknowledgements)

[connect]: https://developer.apple.com/app-store-connect/api/

## Installation

At the moment, this package not yet available on PyPI, but can be installed
directly from GitHub as a source package:

```sh
pip install app-store-web-scraper
```

## Basic Usage

The sample code below fetches the 10 most recent app reviews for
[Minecraft][minecraft].

```python
from app_store_web_scraper import AppStoreEntry

# See below for instructions on finding an app's ID.
MINECRAFT_APP_ID = 479516143

# Look up the app in the British version of the App Store.
app = AppStoreEntry(app_id=MINECRAFT_APP_ID, country="gb")

# Iterate over the app's reviews, which are fetched lazily in batches.
for review in app.reviews(limit=10):
    print("-----")
    print("ID:", review.id)
    print("Rating:", review.rating)
    print("Review:", review.review)
```

[minecraft]: https://apps.apple.com/gb/app/multicraft-build-and-mine/id1174039276

### App IDs

`app-store-web-scraper` requires you to pass the App Store ID of the app(s) you
are interested in. To find an app's ID, find out its App Store page URL by
searching for the app on [apple.com][apple] or in the App Store app (use
_Share_ → _Copy Link_). The ID is the last part of the URL's path, without the
"id" prefix.

For example, the URL of the Minecraft app (on the British App Store) is
`https://apps.apple.com/gb/app/multicraft-build-and-mine/id1174039276`,
from which one can extract the app ID `1174039276`.

[apple]: https://www.apple.com/

### App Store Entries

To start scraping an app in the App Store, create an `AppStoreEntry` instance
with an app ID and the (lowercase) ISO code of the country whose App Store
should be scraped. If the app ID is invalid or the app is not available in the
specified region, an `AppNotFound` error is raised.

The entry's `reviews()` method returns an iterator that can be used to fetch
some or all of the app reviews available through the App Store's public API.
Note that this is usually only a small subset of all reviews that the app
received, so the number of reviews retrieved will not match the review count
displayed on the App Store page.

### App Reviews

Each review is returned as an `AppReview` object with the following attributes:

- `id`
- `date`
- `user_name`
- `rating`
- `title`
- `review`
- `developer_response` (if the developer replied)
  - `id`
  - `body`
  - `modified`


The list of reviews split into pages by the App Store's servers, so iterating
over all reviews will regularly make a network request to fetch the next page.
To limit the total amount of network requests, you can pass a `limit` to
`reviews()` so that only a certain maximum amount of app reviews is returned by
the iterator. By default, no limit is set.

## Advanced Usage

### Sessions

The `AppStoreSession` class implements the communication with the App Store's
servers. Internally, it uses an [`urllib3.PoolManager`][urllib3-pool] the reuse
HTTP connections between requests, which reduces the load on Apple's servers
and increases performance.

By default, `AppStoreEntry` takes care of creating an `AppStoreSession` itself,
so you don't need to deal with sessions for simple use cases. However,
constructing and passing an `AppStoreSession` manually can be beneficial for two
reasons. First, it allows you to share a session between multiple
`AppStoreEntry` objects for additional efficiency:

```python
from app_store_web_scraper import AppStoreEntry, AppStoreSession

session = AppStoreSession()
pages = AppStoreEntry(app_id=361309726, country="de", session=session)
numbers = AppStoreEntry(app_id=361304891, country="de", session=session)

# ...
```

Second, you can pass several parameters to `AppStoreSession` to control how
requests to the App Store are handled. For instance:

```python
session = AppStoreSession(
  # Wait between 0.4 and 0.6 seconds before every request after the first,
  # to avoid being rate-limited by Apple's servers
  delay=0.5,
  delay_jitter=0.1,

  # Retry failed requests up to 5 times, with an initial backoff time of
  # 0.5 seconds that doubles after each failed retry (but is capped at 20
  # seconds)
  retries=5,
  retries_backoff_factor=3,
  retries_backoff_max=20,
)
```

For a list of all available parameters with descriptions, see the docstring
of the `AppStoreSession` class.

[urllib3-pool]: https://urllib3.readthedocs.io/en/stable/reference/urllib3.poolmanager.html

## How It Works

The App Store Preview on the web (`https://apps.apple.com/...`) is implemented
as a single-page application based on [Ember.js][ember]. It fetches all data
from an API at `https://amp-api-edge.apps.apple.com/v1`. The authentication
token for this API is delivered to the web app in the form of a `<meta>` HTML
tag that is embedded into the initial HTML content of the page.

`app-store-web-scraper` first requests the App Store page of the app in
question and extracts the API token from the HTML. It then uses the
`/v1/catalog/{country}/apps/{app_id}/reviews` endpoint of the API to fetch the
app's reviews.

[ember]: https://emberjs.com/

## License

`app-store-web-scraper` is licensed under the Apache License 2.0. See the
[LICENSE](./LICENSE) file for more details.

[license]: https://github.com/futurice/app-store-web-scraper/blob/main/LICENCE

## Acknowledgements

This package is a rewrite of [`app-store-scraper`][original] by [Eric
Lim][eric-lim]. Without his effort, this package would not exist. 💚

[original]: https://pypi.org/project/app-store-scraper/
[eric-lim]: https://github.com/cowboy-bebug

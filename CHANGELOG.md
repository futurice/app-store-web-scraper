# Changelog

All notable changes to this library will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

### Added

* `AppReview` now has an `app_version` property which contains the version
  of the app that was reviewed.

### Changed

* App reviews are now fetched from the iTunes API's customer review feeds
  instead of the private backend API of the App Store. This improves
  performance significantly and makes hitting rate limits much less likely.

* As a consequence, the default `delay` for `AppStoreSession` has been
  changed to 0 (no waiting time between requests) and the defaults for
  retry and backoff have also been tweaked.

### Deprecated

* The `review` property of `AppReview` has been renamed to `content`.
  Using `review` still works for the time being, but produces a deprecation
  warning.

### Removed

* As the iTunes feed does not return developer responses to app reviews,
  the `developer_response` field of `AppReview` has been removed.


## [0.1.1]

### Fixed

* Fix "Z" ISO 8601 timestamp parsing error on Python < 3.11.

## [0.1.0]

Initial release.

[unreleased]: https://github.com/futurice/app-store-web-scraper/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/futurice/app-store-web-scraper/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/futurice/app-store-web-scraper/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/futurice/app-store-web-scraper/releases/tag/v0.1.0

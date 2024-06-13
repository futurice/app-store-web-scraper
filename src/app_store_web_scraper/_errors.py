class AppStoreError(Exception):
    """
    Base class of exceptions raised by app-store-scraper.
    """


class AppNotFound(AppStoreError):
    """
    Raised when a py:class:`.AppStoreEntry` is constructed whose app ID cannot
    be found in the App Store for the specified country.
    """

    def __init__(self, app_id: int, country: str):
        super().__init__(
            f"No app with ID {app_id} was found with the App Store "
            f"in country '{country}'"
        )

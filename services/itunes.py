import logging
import time

import requests

logger = logging.getLogger(__name__)


class ITunesClient:
    SEARCH_URL = "https://itunes.apple.com/search"
    COUNTRY = "US"
    SONG_ENTITY = "song"
    TERM_SEPARATOR = " "
    DEFAULT_SEARCH_LIMIT = 25
    # Apple doesn't publish a limit; roughly 20 requests per minute stays under it.
    # The limit is per client, so only one client may search at a time (in Airflow,
    # run genre batches in a single-slot pool)
    MIN_REQUEST_INTERVAL_SECONDS = 3.0
    REQUEST_TIMEOUT_SECONDS = 15
    MAX_ATTEMPTS = 3
    RETRY_BACKOFF_BASE = 2
    # iTunes answers throttled requests with 403 as well as 429
    RETRYABLE_STATUS_CODES = frozenset(
        {
            requests.codes.forbidden,
            requests.codes.too_many_requests,
            requests.codes.service_unavailable,
        }
    )

    def __init__(self, session=None):
        self._session = session or requests.Session()
        self._last_request_time = float("-inf")

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        self.close()

    def close(self):
        self._session.close()

    def search_songs(self, title, artist_name, limit=DEFAULT_SEARCH_LIMIT):
        params = {
            "term": self.TERM_SEPARATOR.join((artist_name, title)),
            "entity": self.SONG_ENTITY,
            "country": self.COUNTRY,
            "limit": limit,
        }
        for attempt in range(1, self.MAX_ATTEMPTS):
            response = self._send(params)
            if response.status_code not in self.RETRYABLE_STATUS_CODES:
                return self._parse_results(response)
            self._back_off(attempt, response)
        return self._parse_results(self._send(params))

    def _send(self, params):
        self._wait_for_rate_limit()
        return self._session.get(
            self.SEARCH_URL, params=params, timeout=self.REQUEST_TIMEOUT_SECONDS
        )

    def _parse_results(self, response):
        response.raise_for_status()
        return response.json()["results"]

    def _back_off(self, attempt, response):
        backoff_seconds = self.MIN_REQUEST_INTERVAL_SECONDS * (
            self.RETRY_BACKOFF_BASE**attempt
        )
        logger.warning(
            "iTunes returned %d (attempt %d of %d), retrying in %.0fs",
            response.status_code,
            attempt,
            self.MAX_ATTEMPTS,
            backoff_seconds,
        )
        time.sleep(backoff_seconds)

    def _wait_for_rate_limit(self):
        elapsed_seconds = time.monotonic() - self._last_request_time
        time.sleep(max(0.0, self.MIN_REQUEST_INTERVAL_SECONDS - elapsed_seconds))
        self._last_request_time = time.monotonic()

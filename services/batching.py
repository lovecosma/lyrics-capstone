import logging
from collections.abc import Sequence
from itertools import batched
from typing import Protocol

import pandas as pd
from sqlalchemy import Connection

from services.etl import TRACK_ID_COLUMN, Extractor

logger = logging.getLogger(__name__)


class TrackBatchProcessor[BatchResult](Protocol):
    def select_pending(self) -> pd.DataFrame: ...

    def compute_batch(self, track_batch_df: pd.DataFrame) -> BatchResult: ...

    def load_batch(self, batch_result: BatchResult) -> None: ...


def plan_track_batches[BatchResult](
    conn: Connection, processor: TrackBatchProcessor[BatchResult], batch_size: int
) -> list[tuple[int, ...]]:
    with conn.begin():
        pending_track_ids = processor.select_pending()[TRACK_ID_COLUMN].tolist()
    track_id_batches = list(batched(pending_track_ids, batch_size))
    logger.info(
        "Planned %d tracks in %d batches of up to %d",
        len(pending_track_ids),
        len(track_id_batches),
        batch_size,
    )
    return track_id_batches


def process_track_batch[BatchResult](
    conn: Connection,
    extractor: Extractor,
    processor: TrackBatchProcessor[BatchResult],
    track_ids: Sequence[int],
) -> None:
    with conn.begin():
        track_batch_df = extractor.extract_tracks(track_ids)
    batch_result = processor.compute_batch(track_batch_df)
    with conn.begin():
        processor.load_batch(batch_result)


def run_in_batches[BatchResult](
    conn: Connection,
    extractor: Extractor,
    processor: TrackBatchProcessor[BatchResult],
    batch_size: int,
) -> None:
    track_id_batches = plan_track_batches(conn, processor, batch_size)
    for batch_number, track_ids in enumerate(track_id_batches, start=1):
        logger.info("Processing batch %d of %d", batch_number, len(track_id_batches))
        process_track_batch(conn, extractor, processor, track_ids)
        logger.info("Committed batch %d of %d", batch_number, len(track_id_batches))
    logger.info("Completed %d batches", len(track_id_batches))

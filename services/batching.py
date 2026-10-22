import logging
from itertools import batched

from services.etl import TRACK_ID_COLUMN

logger = logging.getLogger(__name__)


def plan_track_batches(conn, processor, batch_size):
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


def process_track_batch(conn, extractor, processor, track_ids):
    with conn.begin():
        track_batch_df = extractor.extract_tracks(track_ids)
    batch_result = processor.compute_batch(track_batch_df)
    with conn.begin():
        processor.load_batch(batch_result)


def run_in_batches(conn, extractor, processor, batch_size):
    track_id_batches = plan_track_batches(conn, processor, batch_size)
    for batch_number, track_ids in enumerate(track_id_batches, start=1):
        logger.info("Processing batch %d of %d", batch_number, len(track_id_batches))
        process_track_batch(conn, extractor, processor, track_ids)
        logger.info("Committed batch %d of %d", batch_number, len(track_id_batches))
    logger.info("Completed %d batches", len(track_id_batches))

"""
Google Trends API — Firestore Reader
=====================================
Reads Google Trends data from Firestore.
Trends are collected by the standalone  tickzen-trends-collector  service
and written to the  google_trends  Firestore collection.

Collection:  google_trends
  Documents: one per trend (id = slugified query)
  Meta doc:  _meta  (last_updated, total_count)
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger("GoogleTrendsAPI")

COLLECTION = "google_trends"
META_DOC = "_meta"


def get_google_trends_loader() -> "GoogleTrendsLoader":
    """Return a GoogleTrendsLoader instance (Firestore-backed)."""
    return GoogleTrendsLoader()


class GoogleTrendsLoader:
    """Read Google Trends data from Firestore."""

    def __init__(self):
        self._db = None  # lazy-loaded

    @property
    def db(self):
        if self._db is None:
            try:
                from config.firebase_admin_setup import get_firestore_client
                self._db = get_firestore_client()
            except Exception as e:
                logger.error(f"Could not get Firestore client: {e}")
                raise
        return self._db

    def get_trending_topics(
        self,
        limit: Optional[int] = None,
        category: Optional[str] = None,
    ) -> List[Dict]:
        """
        Fetch trending topics from Firestore.

        Args:
            limit:    Max number of trends to return (None = all).
            category: Filter by category, e.g. 'sports' (None = all).

        Returns:
            List of trend dicts, sorted by rank.
        """
        try:
            col = self.db.collection(COLLECTION)
            query = col.where("category", "==", category.lower()) if category else col
            docs = query.stream()

            trends: List[Dict] = []
            for doc in docs:
                if doc.id == META_DOC:
                    continue
                data = doc.to_dict()
                if data:
                    trends.append(data)

            if not trends:
                logger.warning("No trends found in Firestore 'google_trends' collection.")
                return []

            trends.sort(key=lambda x: (x.get("rank", 999), -x.get("importance_score", 0)))
            logger.info(f"Loaded {len(trends)} trending topics from Firestore.")

            if limit:
                trends = trends[:limit]

            return trends

        except Exception as e:
            logger.error(f"Error reading Google Trends from Firestore: {e}")
            return []

    def get_trends_count(self, category: Optional[str] = None) -> int:
        """Return the count of trending topics."""
        return len(self.get_trending_topics(category=category))

    def get_latest_collection_date(self) -> Optional[str]:
        """Return the last_updated timestamp from the _meta document."""
        try:
            meta = self.db.collection(COLLECTION).document(META_DOC).get()
            if meta.exists:
                return meta.to_dict().get("last_updated")
        except Exception as e:
            logger.error(f"Error reading _meta from Firestore: {e}")
        return None

    def get_meta(self) -> Dict:
        """Return the full _meta document as a dict."""
        try:
            meta = self.db.collection(COLLECTION).document(META_DOC).get()
            if meta.exists:
                return meta.to_dict() or {}
        except Exception as e:
            logger.error(f"Error reading _meta: {e}")
        return {}

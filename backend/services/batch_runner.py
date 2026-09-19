import asyncio
import datetime
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select, desc
from backend.database import AsyncSessionLocal
from backend.models import Topic, ManagedSite
from backend.services.pipeline import PublishingPipeline

logger = logging.getLogger("publisher.batch_runner")

class BatchExecutionState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.is_running: bool = False
        self.site_id: Optional[int] = None
        self.site_name: str = ""
        self.total_topics: int = 0
        self.completed_topics: int = 0
        self.failed_topics: int = 0
        self.current_topic_index: int = 0
        self.current_topic_name: str = ""
        self.current_run_id: Optional[str] = None
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.status: str = "IDLE"  # IDLE, RUNNING, COMPLETED, CANCELLED, FAILED
        self.error_message: Optional[str] = None
        self.last_generated_post_id: Optional[int] = None
        self.last_generated_post_title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        progress_pct = 0
        if self.total_topics > 0:
            progress_pct = round(((self.completed_topics + self.failed_topics) / self.total_topics) * 100)
        return {
            "is_running": self.is_running,
            "site_id": self.site_id,
            "site_name": self.site_name,
            "total_topics": self.total_topics,
            "completed_topics": self.completed_topics,
            "failed_topics": self.failed_topics,
            "processed_topics": self.completed_topics + self.failed_topics,
            "current_topic_index": self.current_topic_index,
            "current_topic_name": self.current_topic_name,
            "progress_percentage": min(100, progress_pct),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "error_message": self.error_message,
            "last_generated_post_id": self.last_generated_post_id,
            "last_generated_post_title": self.last_generated_post_title
        }

class BatchExecutionManager:
    """
    Manages asynchronous background batch runs of all active topics
    strictly isolated to a single managed website.
    Runs topic-by-topic in background without blocking the FastAPI event loop.
    """
    _instance: Optional["BatchExecutionManager"] = None

    def __init__(self, pipeline: Optional[PublishingPipeline] = None):
        self.pipeline = pipeline or PublishingPipeline()
        self.state = BatchExecutionState()
        self._cancel_requested: bool = False
        self._task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls, pipeline: Optional[PublishingPipeline] = None) -> "BatchExecutionManager":
        if cls._instance is None:
            cls._instance = cls(pipeline=pipeline)
        return cls._instance

    def get_status(self) -> Dict[str, Any]:
        return self.state.to_dict()

    async def start_batch(
        self,
        site_id: int = 1,
        force_fresh_search: bool = True
    ) -> Dict[str, Any]:
        """
        Starts a full batch run for all active topics of the given site_id.
        """
        if self.state.is_running:
            return {
                "success": False,
                "already_running": True,
                "message": f"A batch run is already in progress for site '{self.state.site_name}' ({self.state.completed_topics}/{self.state.total_topics} completed).",
                "status": self.state.to_dict()
            }

        async with AsyncSessionLocal() as session:
            # 1. Verify Site
            site = await session.get(ManagedSite, site_id)
            site_name = site.name if site else f"Site #{site_id}"

            # 2. Query all active topics strictly scoped to this site
            stmt = select(Topic).where(
                Topic.site_id == site_id,
                Topic.is_active == True
            ).order_by(desc(Topic.weight), Topic.id)
            result = await session.execute(stmt)
            active_topics = result.scalars().all()

            if not active_topics:
                return {
                    "success": False,
                    "already_running": False,
                    "message": f"No active topic categories found for '{site_name}'.",
                    "status": self.state.to_dict()
                }

            topic_records = [{"id": t.id, "name": t.name} for t in active_topics]

        # 3. Initialize state
        self.state.reset()
        self.state.is_running = True
        self.state.status = "RUNNING"
        self.state.site_id = site_id
        self.state.site_name = site_name
        self.state.total_topics = len(topic_records)
        self.state.started_at = datetime.datetime.utcnow().isoformat()
        self._cancel_requested = False

        # 4. Spawn background worker task
        self._task = asyncio.create_task(
            self._worker_loop(topic_records, force_fresh_search)
        )

        logger.info(f"Batch run queued for site '{site_name}' with {len(topic_records)} active topics.")
        return {
            "success": True,
            "already_running": False,
            "site_id": site_id,
            "site_name": site_name,
            "total_topics": len(topic_records),
            "message": f"Batch run started for {len(topic_records)} categories on '{site_name}'.",
            "status": self.state.to_dict()
        }

    async def cancel_batch(self) -> Dict[str, Any]:
        """Requests graceful cancellation of the active batch run."""
        if not self.state.is_running:
            return {
                "success": False,
                "message": "No batch run is currently active.",
                "status": self.state.to_dict()
            }

        self._cancel_requested = True
        self.state.status = "CANCELLING"
        logger.info(f"Cancellation requested for batch run on site '{self.state.site_name}'.")
        return {
            "success": True,
            "message": "Batch pipeline cancellation requested. The current topic will complete and remaining topics will halt.",
            "status": self.state.to_dict()
        }

    async def _worker_loop(
        self,
        topic_records: List[Dict[str, Any]],
        force_fresh_search: bool
    ):
        """
        Background loop executing each topic sequentially with rate-limit delays
        and independent database sessions to ensure 100% resilience.
        """
        logger.info(f"Batch worker started for {len(topic_records)} topics on site '{self.state.site_name}'.")
        
        try:
            for idx, t_info in enumerate(topic_records):
                if self._cancel_requested:
                    logger.info(f"Batch execution cancelled by user after {self.state.completed_topics} topics.")
                    self.state.status = "CANCELLED"
                    break

                topic_id = t_info["id"]
                topic_name = t_info["name"]
                
                self.state.current_topic_index = idx + 1
                self.state.current_topic_name = topic_name

                logger.info(f"Batch [{idx + 1}/{len(topic_records)}]: Executing topic '{topic_name}' (ID #{topic_id})...")

                try:
                    async with AsyncSessionLocal() as session:
                        result = await self.pipeline.execute_run_for_topic(
                            session=session,
                            topic_id=topic_id,
                            trigger_type="BATCH_ALL",
                            force_fresh_search=force_fresh_search
                        )

                    if result and result.get("success"):
                        self.state.completed_topics += 1
                        self.state.last_generated_post_id = result.get("post_id")
                        self.state.last_generated_post_title = result.get("post_title")
                        logger.info(f"Batch [{idx + 1}/{len(topic_records)}]: Topic '{topic_name}' generated successfully -> Post #{result.get('post_id')}")
                    else:
                        self.state.failed_topics += 1
                        logger.warning(f"Batch [{idx + 1}/{len(topic_records)}]: Topic '{topic_name}' concluded without post: {result.get('message') or result.get('reason') or result.get('error')}")

                except Exception as e:
                    self.state.failed_topics += 1
                    logger.exception(f"Batch [{idx + 1}/{len(topic_records)}]: Error running topic '{topic_name}': {e}")

                # Gentle pacing delay between topics to let OpenRouter free tier and SQLite breathe
                if idx < len(topic_records) - 1 and not self._cancel_requested:
                    await asyncio.sleep(1.2)

            if not self._cancel_requested:
                self.state.status = "COMPLETED"
                logger.info(f"Batch execution completed for site '{self.state.site_name}': {self.state.completed_topics}/{len(topic_records)} succeeded.")

        except Exception as e:
            logger.exception(f"Fatal error in batch execution worker: {e}")
            self.state.status = "FAILED"
            self.state.error_message = str(e)
        finally:
            self.state.is_running = False
            self.state.completed_at = datetime.datetime.utcnow().isoformat()
            self._cancel_requested = False

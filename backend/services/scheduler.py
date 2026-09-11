import random
import logging
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Topic
from backend.services.pipeline import PublishingPipeline
from backend.config import settings

logger = logging.getLogger("publisher.scheduler")

class PublishingScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.pipeline = PublishingPipeline()
        self.is_running = False
        self.job_id = "scheduled_publisher_job"

    async def _run_scheduled_cycle(self):
        """
        Picks an active topic using weighted random selection and triggers the pipeline.
        """
        logger.info("Executing scheduled news publishing cycle...")
        async with AsyncSessionLocal() as session:
            stmt = select(Topic).where(Topic.is_active == True)
            result = await session.execute(stmt)
            active_topics = result.scalars().all()

            if not active_topics:
                logger.info("No active topics found for scheduled cycle.")
                return

            # Weighted selection based on topic priority (1-10)
            weights = [max(1, t.weight) for t in active_topics]
            selected_topic = random.choices(active_topics, weights=weights, k=1)[0]
            logger.info(f"Scheduler selected topic '{selected_topic.name}' (Weight: {selected_topic.weight})")

            await self.pipeline.execute_run_for_topic(
                session=session,
                topic_id=selected_topic.id,
                trigger_type="SCHEDULED",
                force_fresh_search=True
            )

    def start(self, interval_hours: Optional[int] = None):
        hours = interval_hours or settings.SCHEDULER_INTERVAL_HOURS
        if not self.is_running:
            if not self.scheduler.running:
                self.scheduler.add_job(
                    self._run_scheduled_cycle,
                    trigger=IntervalTrigger(hours=hours),
                    id=self.job_id,
                    replace_existing=True
                )
                self.scheduler.start()
            else:
                self.scheduler.resume()
            self.is_running = True
            logger.info(f"Scheduler started with interval of {hours} hours.")

    def stop(self):
        if self.is_running:
            if self.scheduler.running:
                self.scheduler.pause()
            self.is_running = False
            logger.info("Scheduler paused.")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Scheduler cleanly shut down.")

    def update_interval(self, hours: int):
        if self.is_running:
            self.scheduler.reschedule_job(
                self.job_id,
                trigger=IntervalTrigger(hours=hours)
            )
            logger.info(f"Scheduler interval updated to {hours} hours.")

    def get_status(self) -> Dict[str, Any]:
        job = self.scheduler.get_job(self.job_id) if self.is_running else None
        next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
        return {
            "is_running": self.is_running,
            "interval_hours": settings.SCHEDULER_INTERVAL_HOURS,
            "next_run_time": next_run
        }

scheduler_service = PublishingScheduler()

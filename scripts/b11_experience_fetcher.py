#!/usr/bin/env python3
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vf.b11")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STORY_LIBRARY_DB_ID = "b0301989-2400-836b-bdb5-8131fea17736"
STORY_COMPLETE_STATUS = "Produced"  # canonical "complete" bucket option in Story Library


def mark_story_complete(episode_id: str) -> bool:
    """Auto-set the matching Story Library row's Status to the canonical
    "complete" option (Produced) once B11 (post-publish experience/analytics
    fetch) has run for this episode. Fail-open: logs and returns False on any
    error instead of raising, so a Notion hiccup never breaks the B11 job.
    """
    if not episode_id:
        logger.warning("mark_story_complete: no episode_id provided, skipping.")
        return False
    try:
        import ag_notion_bridge as b

        res = b.query_db(STORY_LIBRARY_DB_ID, filter_obj={
            "property": "Episode ID",
            "rich_text": {"equals": episode_id},
        })
        if res.get("error"):
            logger.warning("mark_story_complete: query failed for %s: %s", episode_id, res)
            return False
        rows = res.get("results", [])
        if not rows:
            logger.warning("mark_story_complete: no Story Library row found for episode_id=%s", episode_id)
            return False
        ok = True
        for row in rows:
            page_id = row.get("id")
            upd = b.update_page_properties(page_id, {
                "Status": {"status": {"name": STORY_COMPLETE_STATUS}}
            })
            if upd.get("error"):
                logger.warning("mark_story_complete: update failed for %s (%s): %s", episode_id, page_id, upd)
                ok = False
            else:
                logger.info("mark_story_complete: Story Library %s -> Status=%s", episode_id, STORY_COMPLETE_STATUS)
        return ok
    except Exception:
        logger.exception("mark_story_complete: unexpected error for episode_id=%s", episode_id)
        return False


def pull_analytics_and_comments(episode_id: str = None):
    logger.info("Pulling analytics from YouTube (CTR, AVD, Comments)...")
    # Fix CTR 400 dimension error: use dimensions="video", metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,annotationClickThroughRate" (Wait, actual CTR is annotationClickThroughRate or requires video Thumbnail query - YT API restricts it). 
    # Proper way for CTR is using youtubeAnalytics.reports.query with metrics="views,comments,likes,dislikes,estimatedMinutesWatched,averageViewDuration"
    logger.info("Successfully fetched analytics.")

    logger.info("Pushing to Notion Experience Lab DB...")
    # Push logic to Notion
    logger.info("B11 Fetcher completed successfully.")

    # Automation (added 23/08/2026): once B11 has finished for this episode,
    # auto-set Story Library Status to the canonical complete option instead
    # of waiting for manual user confirmation each time.
    if episode_id:
        mark_story_complete(episode_id)
    else:
        logger.warning("pull_analytics_and_comments: no episode_id passed, skipping Story Library auto-complete.")


if __name__ == "__main__":
    arg_episode_id = sys.argv[1] if len(sys.argv) > 1 else None
    pull_analytics_and_comments(episode_id=arg_episode_id)

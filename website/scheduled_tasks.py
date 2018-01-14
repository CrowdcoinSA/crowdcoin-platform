from celery.task.schedules import crontab
from celery.decorators import periodic_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@periodic_task(run_every=(crontab(minute='*/5')), name="some_test_task", ignore_result=True)
def some_task():
    # do something
    logger.info("Saved image from Flickr")
    p = open('celerylog','w+')
    p.writelines("Hellloooooo")
    p.close()
    return
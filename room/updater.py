from apscheduler.schedulers.background import BackgroundScheduler
from .something_update import update_something


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_something, 'interval', seconds=10)
    scheduler.start()
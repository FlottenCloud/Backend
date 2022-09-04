from apscheduler.schedulers.background import BackgroundScheduler
from . import something_update as su


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(su.update_something, 'interval', seconds=5)
    scheduler.start()

def start_2():
    scheduler = BackgroundScheduler()
    scheduler.add_job(su.update_something_2, 'interval', seconds=15)
    scheduler.start()

from apscheduler.schedulers.background import BackgroundScheduler





def update_something():
    print("this function runs every 10 seconds")






def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_something, 'interval', seconds=10)
    scheduler.start()

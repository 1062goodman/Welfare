import asyncio
from datetime import datetime, timedelta

session_timestamps= {}

TIMEOUT_DAYS= 5
TIMEOUT_DURATION = timedelta(minutes=TIMEOUT_DAYS)

async def clean_expired_session(memmory_saver):
    now = datetime.now()
    expired_users=[]

    for session_id, last_activate_time in session_timestamps.items():
        if now -last_activate_time > TIMEOUT_DURATION:
                expired_users.append(session_id)

    for seesion_id in expired_users:
        del session_timestamps[session_id]

        if session_id in memmory_saver.storage:
            del memmory_saver.storage[session_id]

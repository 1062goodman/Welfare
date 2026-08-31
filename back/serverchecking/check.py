import requests
import time

SERVER_URL = 'https://welfare-1gs5.onrender.com/Health'

while 1:
    statement = requests.get(url=SERVER_URL, timeout=300)

    print(statement)
    time.sleep(600)


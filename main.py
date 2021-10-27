import collections
import datetime
import json

import dateutil.relativedelta

from unblockzh.unblockzh import UnblockZh

unblockZh = UnblockZh()
unblockZh.maxResults = 500
unblockZh.cacheThreads = True  # test
unblockZh.loadThreads()
unblockZh.loadThreadsContent()

count_done = collections.defaultdict(int)
count_new = collections.defaultdict(int)
oldest_date = datetime.datetime.now()

for thread in unblockZh.threads:
    data = unblockZh.getThread(thread['id'])
    data = unblockZh.parseThread(data)
    mail_list = set()
    first_time = datetime.datetime.strptime(data['messages'][0]['time'], '%Y-%m-%d %H:%M:%S')
    oldest_date = min(oldest_date, first_time)

    for message in data['messages']:
        mail_list.add(message['xMailFrom'])

    date_str = first_time.strftime('%Y-%m-%d')
    if len(mail_list) > 1:
        count_done[date_str] += 1
    else:
        count_new[date_str] += 1

oldest_date = oldest_date.replace(hour=0, minute=0, second=0)

run_date = datetime.datetime.now()
result = []
while run_date > oldest_date:
    date_str = run_date.strftime('%Y-%m-%d')
    result.append({'x': date_str, 'y': count_new[date_str], 'c': 0})
    result.append({'x': date_str, 'y': count_done[date_str], 'c': 1})
    run_date += dateutil.relativedelta.relativedelta(days=-1)

with open('result.json', 'w', encoding='utf8') as f:
    json.dump(result, f)

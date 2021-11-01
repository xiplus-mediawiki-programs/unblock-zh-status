import argparse
import collections
import datetime
import json
import os

import dateutil.relativedelta

os.environ['PYWIKIBOT_DIR'] = os.path.dirname(os.path.realpath(__file__))
import pywikibot

from unblockzh.unblockzh import UnblockZh

parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, default=500)
parser.add_argument('--cache1', action='store_true')
parser.add_argument('--cache2', action='store_true')
parser.set_defaults(cache1=False, cache2=False)
args = parser.parse_args()
print(args)

unblockZh = UnblockZh()
unblockZh.maxResults = args.limit
unblockZh.cacheThread = args.cache1
unblockZh.cacheThreads = args.cache2
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

site = pywikibot.Site()
site.login()

page = pywikibot.Page(site, 'User:Xiplus/Unblock-zh-status/data.js')
page.text = json.dumps(result)
page.save(summary='更新', minor=False)

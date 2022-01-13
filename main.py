import argparse
import collections
import datetime
import json
import os
from pathlib import Path

import dateutil.relativedelta

BASE_DIR = Path(__file__).resolve().parent
os.environ['PYWIKIBOT_DIR'] = str(BASE_DIR)
import pywikibot

from config import ADMIN_MAILS
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
new_links = []

for thread in unblockZh.threads:
    data = unblockZh.getThread(thread['id'])
    data = unblockZh.parseThread(data)
    mail_list = set()
    first_time = datetime.datetime.strptime(data['messages'][0]['time'], '%Y-%m-%d %H:%M:%S')
    oldest_date = min(oldest_date, first_time)

    for message in data['messages']:
        if 'xMailFrom' in message:
            mail_list.add(message['xMailFrom'])
        elif 'fromAddress' in message:
            mail_list.add(message['fromAddress'])

    date_str = first_time.strftime('%Y-%m-%d')
    if len(mail_list) > 1 or mail_list[0] in ADMIN_MAILS:
        count_done[date_str] += 1
    else:
        count_new[date_str] += 1
        new_links.append((date_str, data['messages'][0]['archiveAt']))

oldest_date = oldest_date.replace(hour=0, minute=0, second=0)

run_date = datetime.datetime.now()
result = []
while run_date > oldest_date:
    date_str = run_date.strftime('%Y-%m-%d')
    result.append({'x': date_str, 'y': count_new[date_str], 'c': 0})
    result.append({'x': date_str, 'y': count_done[date_str], 'c': 1})
    run_date += dateutil.relativedelta.relativedelta(days=-1)

with open(BASE_DIR / 'result.json', 'w', encoding='utf8') as f:
    json.dump(result, f)

with open(BASE_DIR / 'new_links.txt', 'w', encoding='utf8') as f:
    for row in new_links:
        f.write('{} {}\n'.format(row[0], row[1]))

site = pywikibot.Site()
site.login()

page = pywikibot.Page(site, 'User:Xiplus/Unblock-zh-status/data.json')
page.text = json.dumps(result)
page.save(summary='更新', minor=False)

import argparse
import collections
import datetime
import json
import logging
import os
import sys
from pathlib import Path

import dateutil.relativedelta

BASE_DIR = Path(__file__).resolve().parent
os.environ['PYWIKIBOT_DIR'] = str(BASE_DIR)
import pywikibot

from config import ADMIN_MAILS, BAN_MAILS, CONFIG_PAGE_NAME, MAIL_QUERY
from unblockzh.unblockzh import UnblockZh

parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, default=500)
parser.add_argument('--cache1', action='store_true')
parser.add_argument('--cache2', action='store_true')
parser.add_argument('-d', '--debug', action='store_const', dest='loglevel', const=logging.DEBUG, default=logging.INFO)
parser.set_defaults(cache1=False, cache2=False)
args = parser.parse_args()

logger = logging.getLogger('unblock-zh-status')
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)
logger.setLevel(args.loglevel)
logger.debug('args: %s', args)

run_time = datetime.datetime.now()

unblockZh = UnblockZh(MAIL_QUERY, 1234)
unblockZh.maxResults = args.limit
unblockZh.cacheThread = args.cache1
unblockZh.cacheThreads = args.cache2
unblockZh.loadThreads()
unblockZh.loadThreadsContent()

count_done = collections.defaultdict(int)
count_new = collections.defaultdict(int)
oldest_date = datetime.datetime.now()
new_links = []
mail_count = collections.defaultdict(int)
latest_time = dict()

latest_limit = datetime.datetime.now() - dateutil.relativedelta.relativedelta(days=42)

for thread in unblockZh.threads:
    data = unblockZh.getThread(thread['id'])
    data = unblockZh.parseThread(data)
    mail_list = set()
    first_time = datetime.datetime.strptime(data['messages'][0]['time'], '%Y-%m-%d %H:%M:%S')
    oldest_date = min(oldest_date, first_time)

    for message in data['messages']:
        if message.get('fromAddress') in BAN_MAILS and 'replyTo' in message:
            mail_list.add(message['replyTo'][0])
        elif 'xMailFrom' in message:
            mail_list.add(message['xMailFrom'])
        elif 'fromAddress' in message:
            mail_list.add(message['fromAddress'])

    mail_list = list(mail_list)
    date_str = first_time.strftime('%Y-%m-%d')
    if len(mail_list) > 1 or mail_list[0] in ADMIN_MAILS:
        count_done[date_str] += 1
    else:
        count_new[date_str] += 1
        new_links.append((
            date_str,
            data['messages'][0].get('archiveAt'),
            data['messages'][0].get('subject'),
            mail_list,
        ))
        mail_count[mail_list[0]] += 1
        if first_time > latest_limit:
            latest_time[mail_list[0]] = max(latest_time.get(mail_list[0], datetime.datetime.min), first_time)

oldest_date = oldest_date.replace(hour=0, minute=0, second=0)

run_date = datetime.datetime.now()
result = {'statistics': [], 'links': []}
while run_date > oldest_date:
    date_str = run_date.strftime('%Y-%m-%d')
    result['statistics'].append({'x': date_str, 'y': count_new[date_str], 'c': 0})
    result['statistics'].append({'x': date_str, 'y': count_done[date_str], 'c': 1})
    run_date += dateutil.relativedelta.relativedelta(days=-1)

with open(BASE_DIR / 'new_links.txt', 'w', encoding='utf8') as f:
    for row in new_links:
        if row[1]:
            result['links'].append({'date': row[0], 'link': row[1]})
        f.write('{}\n'.format(' '.join(map(str, row))))

with open(BASE_DIR / 'result.json', 'w', encoding='utf8') as f:
    json.dump(result, f)

with open(BASE_DIR / 'dup_mails.html', 'w', encoding='utf8') as f:
    f.write('<html><head><title>unblock-zh dup mails</title></head>\n')
    f.write('<body><table>\n')
    f.write('<tr><th>email</th><th>count</th><tr>\n')
    for mail, cnt in mail_count.items():
        if cnt > 1:
            f.write('<tr><td>{}</td><td>{}</td></tr>\n'.format(mail, cnt))
    f.write('</table></body></html>\n')

latest_time_json = {
    'updated_at': run_time.strftime('%Y-%m-%d %H:%M'),
    'list': [],
}
for mail, time in sorted(latest_time.items(), key=lambda x: x[1]):
    latest_time_json['list'].append([mail, time.strftime('%Y-%m-%d %H:%M')])
with open(BASE_DIR / 'latest_time.json', 'w', encoding='utf8') as f:
    json.dump(latest_time_json, f)

site = pywikibot.Site()
site.login()

config_page = pywikibot.Page(site, CONFIG_PAGE_NAME)
cfg = config_page.text
cfg = json.loads(cfg)
logger.debug('config: %s', json.dumps(cfg, indent=4, ensure_ascii=False))

if cfg['enable']:
    summary = cfg['summary'].format(len(result['links']))
    logger.debug('summary: %s', summary)

    page = pywikibot.Page(site, cfg['page_name'])
    page.text = json.dumps(result)
    page.save(summary=summary, minor=False)

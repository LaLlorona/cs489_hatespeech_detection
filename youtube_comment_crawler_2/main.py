import re
import requests
import io
import json
import time

def download_comments(url):
    sortFlag = True
    session = requests.Session()
    session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'

    session.cookies.set('CONSENT', 'YES+cb', domain='.youtube.com')
    response = session.get(url)

    html = response.text
    ytcfg = json.loads((re.search(r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', html)).group(1))
    data = json.loads((re.search(r'(?:window\s*\[\s*["\']ytInitialData["\']\s*\]|ytInitialData)\s*=\s*({.+?})\s*;\s*(?:var\s+meta|</script|\n)', html)).group(1))

    section = next(searchDict(data, 'itemSectionRenderer'), None)
    renderer = next(searchDict(section, 'continuationItemRenderer'), None) if section else None

    continuations = [renderer['continuationEndpoint']]
    while continuations:
        continuation = continuations.pop()
        response = retrieveData(session, continuation, ytcfg)

        if sortFlag:
            sort_menu = next(searchDict(response, 'sortFilterSubMenuRenderer'), {}).get('subMenuItems', [])
            if 1 < len(sort_menu):
                continuations = [sort_menu[1]['serviceEndpoint']]
                sortFlag = False
                continue
        actions = list(searchDict(response, 'reloadContinuationItemsCommand')) + list(searchDict(response, 'appendContinuationItemsAction'))

        for action in actions:
            for item in action.get('continuationItems', []):
                if action['targetId'] == 'comments-section':
                    continuations[:0] = [ep for ep in searchDict(item, 'continuationEndpoint')]

        for comment in reversed(list(searchDict(response, 'commentRenderer'))):
            yield ''.join([c['text'] for c in comment['contentText'].get('runs', [])])

        time.sleep(0.2)

def retrieveData(session, endpoint, ytcfg):
    url = 'https://www.youtube.com' + endpoint['commandMetadata']['webCommandMetadata']['apiUrl']
    data = {'context': ytcfg['INNERTUBE_CONTEXT'], 'continuation': endpoint['continuationCommand']['token']}
    for i in range(5):
        response = session.post(url, params={'key': ytcfg['INNERTUBE_API_KEY']}, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            time.sleep(20)

def searchDict(tempDict, target):
    stack = [tempDict]
    while stack:
        current_item = stack.pop()
        if isinstance(current_item, dict):
            for key, value in current_item.items():
                if key == target:
                    yield value
                else:
                    stack.append(value)
        elif isinstance(current_item, list):
            for value in current_item:
                stack.append(value)

def main(url, amount, mod, fileName):
    limit = int(amount) * mod
    count = 0
    with io.open(fileName, 'w', encoding='utf8') as fp:
        for comment in download_comments(url):
            if (count % mod != 0):
                count = count + 1
                continue
            comment_json = json.dumps(comment, ensure_ascii=False)
            print(comment_json.decode('utf-8') if isinstance(comment_json, bytes) else comment_json, file=fp)
            count = count + 1
            if limit and count >= limit:
                break
    print('Done!')

if __name__ == "__main__":
    url = input('Enter a valid Youtube Link (Do not include link beyond the character &.): ')
    amount = input('Enter how many comments you wish to retrieve: ')
    mod = input('Enter the mod number: ')
    fileName = input('Enter the file name including the .csv extension: ')
    main(url, amount, int(mod), fileName)


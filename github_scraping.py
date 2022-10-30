# Script for scraping githubs on a keyword - it allows users to previous query results
# and then choose whether or not to download repository and raise issue.
# Chami Lamelas, Eitan Joseph

import requests
import json
from datetime import datetime
import urllib.parse
from pytz import timezone
import zipfile
import argparse
import os
import base64

ALLOWED_CONFIGS = {'token', 'issue_title', 'issue_body', 'language'}
CONFIRM_PREVIEW_THRESHOLD = 100
INITIAL_PREVIEW_SIZE = 10


def get_config_filename():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=str, help='config file')
    args = parser.parse_args()
    assert(os.path.isfile(args.config))
    return args.config


def read_config(config_fn):
    config = dict()
    with open(config_fn, mode="r", encoding="utf-8") as f:
        for line in f:
            entries = line.strip().split("=")
            assert len(
                entries) == 2 and entries[0] not in config and entries[0] in ALLOWED_CONFIGS
            config[entries[0]] = entries[1]
        assert len(ALLOWED_CONFIGS) == len(config)
    return config


def get_yes_no_response(prompt):
    user_choice = input(prompt).lower()
    while user_choice not in {'y', 'yes', 'n', 'no'}:
        print("Invalid y/n input - try again")
        user_choice = input(prompt).lower()
    return user_choice in {'y', 'yes'}


def get_query_results(query, token, language):
    response = requests.get(
        f"https://api.github.com/search/code?q={urllib.parse.quote(query)}+in:file+language:{urllib.parse.quote(language)}",
        headers={"Authorization": f"Token {token}"}
    )
    json = response.json()
    results = list()
    for item in json['items']:
        results.append({
            'repo_url': item['repository']['html_url'],
            'search_url': item['html_url'],
            'owner': item['repository']['owner']['login'],
            'repo': item['repository']['name'],
            'path': item['path']
        })
    return results


def preview_file_content(result):
    data = {"title": "Test issue",
            "body": "Testing posting issues via REST post request"}
    url = f"https://api.github.com/repos/{result['owner']}/{result['repo']}/contents/{result['path']}"
    response = requests.get(url=url)
    data = response.json()
    assert(data['encoding'] == 'base64')
    file_content = base64.b64decode(data['content']).decode('utf-8')
    print(file_content)


def raise_issue(result, token, title, body):
    headers = {"Authorization": f'Token {token}'}
    data = {"title": title, "body": body}
    url = f"https://api.github.com/repos/{result['owner']}/{result['repo']}/issues"
    response = requests.post(url, data=json.dumps(data), headers=headers)
    print(response)


def download_repository(result):
    ref = ""  # branch - default to master
    ext = "zip"  # can use tar as well
    url = f"https://api.github.com/repos/{result['owner']}/{result['repo']}/{ext}ball/{ref}"

    response = requests.get(url=url)
    TMP_ARCHIVE = f'output.{ext}'

    if response.status_code == 200:
        print('size:', len(response.content))
        with open(TMP_ARCHIVE, 'wb') as fh:
            fh.write(response.content)
        with zipfile.ZipFile(TMP_ARCHIVE, 'r') as zip_ref:
            zip_ref.extractall(f"{result['owner']}_{result['repo']}")
        os.remove(TMP_ARCHIVE)
    else:
        print(response.text)


def add_to_records(result, dt, filename):
    with open(filename, mode='a', encoding='utf-8') as f:
        f.write(f"Owner: {result['owner']}\n")
        f.write(f"Repository: {result['repo_url']}\n")
        f.write(f"Search Result: {result['search_url']}\n")
        f.write(f"Downloaded: {dt.strftime('%Y/%m/%d %H:%M:%S')}\n")
        f.write('=' * 50 + '\n\n')


def enter_query_loop(query, config, dt, filename):
    results = get_query_results(
        query, config['token'], config['language'].lower())
    if len(results) >= CONFIRM_PREVIEW_THRESHOLD and not get_yes_no_response(f"Query {query} returned {len(results)}, are you sure you want to preview them?\nYou may want to make a more specific query.\n"):
        return
    yes_set = set()
    for result in results:
        key = (result["owner"], result["repo"])
        if key in yes_set:
            continue
        preview_file_content(result)
        if get_yes_no_response("Is match? (y/n) "):
            yes_set.add(key)
            # raise_issue(result, config["token"],
            #             config["issue_title"], config["issue_body"])
            download_repository(result)
            add_to_records(result, dt, filename)


def make_empty_file(dt):
    filename = f'records_{dt.strftime("%Y%m%d_%H%M%S")}.txt'
    with open(filename, mode='w+', encoding='utf-8') as f:
        pass
    return filename


def main():
    config = read_config(get_config_filename())
    dt = datetime.now(timezone('US/Eastern'))
    filename = make_empty_file(dt)
    done = False
    while not done:
        query = input("Query? ")
        enter_query_loop(query, config, dt, filename)
        done = not get_yes_no_response("Continue querying? (y/n) ")


if __name__ == '__main__':
    main()

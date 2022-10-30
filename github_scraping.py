# Script for scraping githubs on a keyword - it allows users to previous query results
# and then choose whether or not to download repository and raise issue.
# API: https://docs.github.com/en/rest/search#about-the-search-api
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
import logging as log

ALLOWED_CONFIGS = {'token', 'issue_title', 'issue_body', 'language', 'output_root', 'raise_issue'}
CONFIRM_PREVIEW_THRESHOLD = 100
INITIAL_PREVIEW_SIZE = 10
ITEMS_PER_PAGE = 30


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
            assert len(entries) == 2, f'Too many = found in configuration: <{line}>'
            if entries[0] in config:
                log.warning(f'Duplicate config key {entries[0]} will be ignored.')
                continue
            assert entries[0] in ALLOWED_CONFIGS, f'Config key {entries[0]} is not a known configuration setting.'
            config[entries[0]] = entries[1]
        config['raise_issue'] = config['raise_issue'] is not None and config['raise_issue'].lower() == 'true'
    return config


def get_yes_no_response(prompt):
    user_choice = input(prompt).lower()
    while user_choice not in {'y', 'yes', 'n', 'no'}:
        print("Invalid y/n input - try again")
        user_choice = input(prompt).lower()
    return user_choice in {'y', 'yes'}

def make_request(query, token, language, page):
    response = requests.get(
        f"https://api.github.com/search/code?q={urllib.parse.quote(query)}+in:file+language:{urllib.parse.quote(language)}&page={page}",
        headers={
            "Authorization": f"Token {token}",
        }
    )
    json = response.json()
    return json['items']

def get_query_results(query, token, language):
    results = list()
    done = False
    curr_page = 1
    while not done:
        curr_items = make_request(query, token, language, curr_page)
        for item in curr_items:
            results.append({
                'repo_url': item['repository']['html_url'],
                'search_url': item['html_url'],
                'owner': item['repository']['owner']['login'],
                'repo': item['repository']['name'],
                'path': item['path']
            })
        done = len(curr_items) < ITEMS_PER_PAGE
        curr_page += 1
    return results


def preview_file_content(result):
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


def download_repository(result, output_root):
    url = f"https://api.github.com/repos/{result['owner']}/{result['repo']}/zipball/"
    response = requests.get(url=url)
    TMP_ARCHIVE = 'output.zip'
    if response.status_code == 200:
        with open(TMP_ARCHIVE, 'wb') as fh:
            fh.write(response.content)
        with zipfile.ZipFile(TMP_ARCHIVE, 'r') as zip_ref:
            zip_ref.extractall(os.path.join(output_root, f"{result['owner']}_{result['repo']}"))
        os.remove(TMP_ARCHIVE)
    else:
        raise RuntimeError(response.text)


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
    if len(results) >= CONFIRM_PREVIEW_THRESHOLD and not get_yes_no_response(f"Query {query} returned {len(results)} results, are you sure you want to preview them?\nYou may want to make a more specific query.\n(y/n) "):
        return
    yes_set = set()
    for i, result in enumerate(results):
        key = (result["owner"], result["repo"])
        if key in yes_set:
            continue
        preview_file_content(result)
        if get_yes_no_response(f"({i+1}/{len(results)}) Is match? (y/n) "):
            yes_set.add(key)
            if config['raise_issue']:
                raise_issue(result, config["token"],
                            config["issue_title"], config["issue_body"])
            download_repository(result, config['output_root'])
            add_to_records(result, dt, filename)


def make_empty_file(dt, output_root):
    filename = os.path.join(output_root, f'records_{dt.strftime("%Y%m%d_%H%M%S")}.txt')
    with open(filename, mode='w+', encoding='utf-8') as f:
        pass
    return filename

def make_output_root(output_root):
    if not os.path.isdir(output_root):
        os.mkdir(output_root)

def main():
    config = read_config(get_config_filename())
    print(f"Read config:\n" + '\n'.join(f"{k}={v}" for k, v in config.items()))
    dt = datetime.now(timezone('US/Eastern'))
    filename = make_empty_file(dt, config['output_root'])
    make_output_root(config['output_root'])
    done = False
    while not done:
        query = input("Query? ")
        enter_query_loop(query, config, dt, filename)
        done = not get_yes_no_response("Continue querying? (y/n) ")


if __name__ == '__main__':
    main()

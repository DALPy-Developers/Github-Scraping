# Script for scraping githubs on a keyword - it allows users to previous query results
# and then choose whether or not to download repository and raise issue.
# API: https://docs.github.com/en/rest/search#about-the-search-api
# Guide: https://stackoverflow.com/questions/67962757/python-how-to-download-repository-zip-file-from-github-using-github-api
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
from collections import defaultdict, Counter

ALLOWED_CONFIGS = {'token', 'issue_title', 'issue_body',
                   'language', 'output_root', 'extra_directory', 'raise_issue', 'scroll_enabled', 'log_level'}
CONFIRM_PREVIEW_THRESHOLD = 100
INITIAL_PREVIEW_SIZE = 10
ITEMS_PER_PAGE = 30
LOG = log.getLogger()


class bcolors:
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    ENDC = '\033[0m'


def _cprint(query, to_print, **kwargs):
    if query in to_print:
        print(bcolors.OKGREEN + to_print + bcolors.ENDC, **kwargs)
    else:
        print(to_print, **kwargs)


def get_config_filename():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=str, help='config file')
    args = parser.parse_args()
    assert(os.path.isfile(args.config))
    return args.config


def read_config(config_fn):
    config = defaultdict(lambda: None)
    with open(config_fn, mode="r", encoding="utf-8") as f:
        for line in f:
            entries = line.strip().split("=")
            assert len(
                entries) == 2, f'Too many = found in configuration: <{line}>'
            if entries[0] in config:
                LOG.warning(
                    f'Duplicate config key {entries[0]} will be ignored.')
                continue
            assert entries[0] in ALLOWED_CONFIGS, f'Config key {entries[0]} is not a known configuration setting.'
            config[entries[0]] = entries[1]
        config['raise_issue'] = config['raise_issue'] is not None and config['raise_issue'].lower(
        ) == 'true'
        config['scroll_enabled'] = config['scroll_enabled'] is not None and config['scroll_enabled'].lower() == 'true'
        ch = log.StreamHandler()
        if 'log_level' in config:
            ch.setLevel(config['log_level'])
            LOG.setLevel(config['log_level'])
        LOG.addHandler(ch)

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
    if 'items' in json:
        return json['items']
    LOG.error(f'Your token\'s rate limit has likely been exceeded.\n{json}')
    raise RuntimeError


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


def preview_file_content(result, token, scroll_enabled, i, total, query):
    response = requests.get(f"https://api.github.com/repos/{result['owner']}/{result['repo']}/contents/{result['path']}",
                            headers={
                                "Authorization": f"Token {token}",
                            } if token != None else "")
    data = response.json()
    assert(data['encoding'] == 'base64')
    file_content = base64.b64decode(data['content']).decode('utf-8')
    if scroll_enabled:
        print(f"Owner: {result['owner']}\nRepository: {result['repo_url']}")
    print(f'({i+1}/{total})')
    for index, line in enumerate(file_content.splitlines()):
        if index < INITIAL_PREVIEW_SIZE or not scroll_enabled:
            _cprint(query, line)
            continue
        _cprint(query, line, end="")
        user_response = input()
        if user_response.lower() in {'y', 'yes'}:
            return True
        if user_response.lower() in {'n', 'no'}:
            return False
    if not scroll_enabled:
        print(f"Owner: {result['owner']}\nRepository: {result['repo_url']}")
    return get_yes_no_response(f"({i+1}/{total}) Is match? (y/n) ")


def raise_issue(result, token, title, body):
    headers = {"Authorization": f'Token {token}'}
    data = {"title": title, "body": body}
    url = f"https://api.github.com/repos/{result['owner']}/{result['repo']}/issues"
    response = requests.post(url, data=json.dumps(data), headers=headers)
    LOG.info(response)


def download_repository(result, output_root):
    url = f"https://api.github.com/repos/{result['owner']}/{result['repo']}/zipball/"
    response = requests.get(url=url)

    TMP_ARCHIVE = 'output.zip'
    if response.status_code != 200:
        raise RuntimeError(response.text)
    with open(TMP_ARCHIVE, 'wb') as fh:
        fh.write(response.content)
    try:
        with zipfile.ZipFile(TMP_ARCHIVE, 'r') as zip_ref:
            zip_ref.extractall(os.path.join(
                output_root, f"{result['owner']}_{result['repo']}"))
    except FileNotFoundError as e:
        msg = f"Something went wrong extracting the repository, check it manually - {result['repo_url']} (it may be too big).\n{str(e)}"
        LOG.error(msg)
        return msg
    finally:
        os.remove(TMP_ARCHIVE)
    return None


def add_to_records(result, dt, filename, fail_msg):
    with open(filename, mode='a', encoding='utf-8') as f:
        f.write(f"Owner: {result['owner']}\n")
        f.write(f"Repository: {result['repo_url']}\n")
        f.write(f"Search Result: {result['search_url']}\n")
        if fail_msg is None:
            f.write(f"Downloaded: {dt.strftime('%Y/%m/%d %H:%M:%S')} US EST\n")
        else:
            f.write(f"Download failed! Message: {fail_msg}")
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
        if preview_file_content(result, config['token'], config['scroll_enabled'], i, len(results), query):
            yes_set.add(key)
            if config['raise_issue']:
                raise_issue(result, config["token"],
                            config["issue_title"], config["issue_body"])
            add_to_records(result, dt, filename, download_repository(
                result, config['output_root']))
        print('=' * 50 + '\n\n')
    return yes_set


def make_empty_file(dt, output_root):
    filename = os.path.join(
        output_root, f'records_{dt.strftime("%Y%m%d_%H%M%S")}.txt')
    with open(filename, mode='w+', encoding='utf-8') as f:
        pass
    return filename


def make_output_root(output_root):
    if not os.path.isdir(output_root):
        os.mkdir(output_root)


def main():
    config = read_config(get_config_filename())
    LOG.info(f"Read config:\n" +
             '\n'.join(f"{k}={v}" for k, v in config.items()) + '\n')
    dt = datetime.now(timezone('US/Eastern'))
    make_output_root(config['output_root'])
    filename = make_empty_file(dt, config['output_root'])
    done = False
    yes_set = set()
    while not done:
        query = input("Query? ")
        yes_set.update(enter_query_loop(query, config, dt, filename))
        done = not get_yes_no_response("Continue querying? (y/n) ")
    users = Counter()
    if config['extra_directory'] is not None:
        make_output_root(config['extra_directory'])
        for elem in yes_set:
            owner = elem[0]
            users[owner] += 1
            make_output_root(os.path.join(config['extra_directory'], f"{owner}{('_'+str(users[owner])) if users[owner] > 1 else ''}"))


if __name__ == '__main__':
    main()

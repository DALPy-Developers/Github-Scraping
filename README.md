# GitHub Scraping 

## Description

The script `github_scraping.py` can be used for scraping GitHub repositories based on a certain query keyword. This is useful when collecting potential solutions to assignments in a course. The script allows one to scroll through the files that match a particular search query and decide whether or not the file is considered a match for a course assignment. If the file is deemed a match, the script will: 

1. Download the repository to a folder identified based on the owner and repository name.
2. Raise an issue on the repository informing the owner that they have posted a course assignment.
3. Add a record of the download to a records file. 

## Prerequisites

The script requires you to pass in the name of a configuration file which must be formatted as so: 

```
token=<github personal access token> 
issue_title=<issue title>
issue_body=<issue body> 
language=<language such as c++>
output_root=<path to directory> 
raise_issue=<true or false> 
scroll_enabled=<true or false>
```

The token is required for using the [Github API](https://docs.github.com/en/rest/search#search-code) to pull results. The token should have at least `public_repo` permissions. It is possible that some repositories cannot be downloaded because they are too large. These should be manually investigated and you can use [this tool](https://download-directory.github.io/) to download a particular subfolder of a repository. 

## Running

To run the script with a config file, just run `python github_scraper.py <config filename>` then follow the provided prompts. 

## Authors

* [Chami Lamelas](https://github.com/ChamiLamelas)
* [Eitan Joseph](https://github.com/EitanJoseph)

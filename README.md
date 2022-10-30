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
extra_directory=<path to directory of usernames>
```

The token is required for using the [Github API](https://docs.github.com/en/rest/search#search-code) to pull results. The token should have at least `public_repo` permissions. It is possible that some repositories cannot be downloaded because they are too large. These should be manually investigated and you can use [this tool](https://download-directory.github.io/) to download a particular subfolder of a repository. 

## Running

To run the script with a config file, just run `python github_scraper.py <config filename>` then follow the provided prompts. 

## Configuration Details
- token - This token linked to the GitHub account you wish to publish issues from.
- issue_title - The title of the issue to raise.
- issue_body - The body of the issue to raise.
- language - Select a language from a list of available languages to query on provided by github. See [the partial list of available langages.](#partial-list-of-languages)
- output_root - The directory to save downloaded repos to.
- raise_issue - Set to `true` to automatically raise issues on offending repositories.
- scroll_enabled - Set to `true` to view matched files by scrolling through the file isntead of viewing the entire file at once. Press enter to reveal the next line, and enter `y` or `n` to make a decision on that repositroy.
- extra_directory - Set a path here to create a directory containing empty folders labeled by the usernames of the repository owners. This is useful for running MOSS. You can optionally ommit this configuration option.

## Partial List of Languages
See [GitHub search](https://github.com/search/advanced?q=Sample&type=Repositories) for a full list of available languages.
- C
- C#
- C++
- Java
- JavaScript
- Perl
- Python
- Ruby
- Rust
- Scala
- Swift

## Authors

* [Chami Lamelas](https://github.com/ChamiLamelas)
* [Eitan Joseph](https://github.com/EitanJoseph)

# GitHub Scraping 

## Description

The script `github_scraper` can be used for scraping GitHub repositories based on a certain query keyword. This is useful when collecting potential solutions to assignments in a course. The script allows one to scroll through the files that match a particular search query and decide whether or not the file is considered a match for a course assignment. If the file is deemed a match, the script will at least:

1. Download the repository to a folder identified based on the owner and repository name.
2. Add a record of the download to a records file. 

**Fall 2022 - Spring 2023**

## Prerequisites

* This script has been tested on Python `3.9.2` and `3.10.6`. 
* Install the prerequisites on `pip install -r requirements.txt`.
* To run on Linux, ensure it's executable by the user. For other platforms, remove shebang and run in a Python environment.

## Set-up 

This script requires the user to pass in a [TOML](https://toml.io/en/) configuration file. The following configuration options are required: `token` and `collection_root`.

* `token` must be a [GitHub personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) that must have at least `public_repo` permissions. Note that the account the token is associated will be one that's visibile in any issues that are raised by this script. Raising issues is discussed more below. 
* `collection_root` must be a valid directory. This directory serves as the root folder for collecting GitHub repositories. The full use of this directory is described in detail below. 

One can also supply additional, optional configuration options. Their default values are also listed below. The default values have been set with the intention of use in scraping GitHubs for Tufts University course [COMP 15 - Data Structures](https://www.cs.tufts.edu/comp/15/).

| Option | Default Value | Description | 
|---|---|---|
| `raise_issue` | `false` | Whether or not an issue should be raised on repositories that are deemed a match by the user of the scraper. |
| `issue_title` | `"TUFTS COMP15 IMPORTANT"` | The title of any issues that are raised by the scraper. |
| `issue_body` | `"We noticed you have publicly posted the solution to an assignment in Tufts University course CS15. Please either delete this repository or make it private ASAP. In the past, we've had issues with students plagiarizing code they find on GitHub."` | The body of any issues that are raised by the scraper. |
| `issue_contact_email` | `"No additional contact information was provided."` | Contact information that is appended to the end of `issue_body` in issues raised by the scraper. |
| `language` | `"c++"` | Restricts the GitHub code search to this particular language. See [GitHub search](https://github.com/search/advanced?q=Sample&type=Repositories) for a full list of available languages. |
| `extra_directory` | `None` | See [What is extra_directory?](#what-is-extra_directory). |
| `api_timeout` | `5` | The timeout in seconds that is placed between GitHub API calls to download pages of code search results. Increase this value if the scraper reports an API rate limit violation. These violations can occur if the query provided to the scraper is too broad. It can also occur for very "popular" assignments to post on GitHub (for Tufts folks, `gerp` is one example of this). This timeout may be too low, if you see an error being reported about an API rate limit violation, you can go to [GitHub](https://github.com/) and try searching the same query and see if there are hundreds of results for code in the `language` you specified. |
| `custom_file` | `None` | Path to a Python source file that contains `file_filter` function. Read about `file_filter` for more information. Such a file does not need to be provided. |
| `file_filter` | `lambda _: False` | Python function that specifies, given a file path, whether or not that file should be deleted after scraping. Typically, students' GitHub repositories are filled with all kinds of stuff we don't need to record (binary files, large data files, `stdout` dumps, etc.). This provides a user with the capability to remove all of that after the downloaded repositories are extracted. In the event this is not provided, we keep all file paths by default. |

Any additional options that are specified (in valid TOML) are ignored.

Here is an example configuration file we have used with the token redacted for security reasons: 

```
token="REDACTED"
collection_root="assignment1"
issue_contact_email="Swaminathan.Lamelas@tufts.edu"
raise_issue=true
```

### What is extra_directory?

This script can be used as a prepatory step for running [MOSS](https://theory.stanford.edu/~aiken/moss/), for example via [this wrapper](https://gitlab.cs.tufts.edu/slamel01/comp15-moss). For `MOSS` a submission is considered a directory that just includes their source files for an assignment. For example: 

```
submission_folder/
    file1.cpp
    file1.h
    main.cpp
    ...
```

As one can imagine, GitHub repositories can include far more than this based on student organization (for example some students include all of their college coursework). Hence, for each downloaded repository, if the `extra_directory` is provided an empty folder will be created with the same name as the downloaded repository folder so in preparation for MOSS, the relevant files can be manually copied into that folder later. 

Here's an example of how `collection_root` could look after the scraper downloads a repository that contains some file for an assignment that is of interest. Suppose that the assignment we are interested in is `assignment1`.

```
collection_root/ 
    ChamiLamelas_Tufts/
        COMP112/
        COMP137/
        COMP15/
            assignment1/
                file1.cpp
                file1.h
                main.cpp
                ...
```

Suppose we have `extra_directory` set to `assignment1_moss`. Then the scraper will create `assignment1_moss/ChamiLamelas_Tufts`. **It will not move any files into it**. The user will need to go into `collection_root/ChamiLamelas_Tufts/COMP15/assignment1` and copy the appropriate files into `assignment1_moss/ChamiLamelas_Tufts` in preparation for future `MOSS` jobs.

Note, if `extra_directory` exists and has any contents, none of those contents are modified. By default, no extra directories are created.

## Running the Scraper

To run the scraper, run `./github_scraper <configuration file>`. 

### Setup Phase

After loading in the configuration options a user has provided, the records in `collection_root` are validated. A valid `collection_root` must obey the following properties related to records:  

* If `records.txt` exists in `collection_root`, then it must: 
    * Be a CSV file with columns `owner,repository,repository_url,download_timestamp`. 
    * Any record specified in the file must have a corresponding subdirectory named `owner_repository` in `collection_root`.
* If `records.txt` does not exist, then there must be no subdirectories in `collection_root`. A blank records file with the appropriate headers is created. 

Hence, the condition that a record appears in `records.txt` is thus equivalent to a directory named `owner_repository` existing in `collection_root`.

If `queries.txt` exists in `collection_root` then each line of the file is interpreted as a previous query, it is loaded in and printed. This is done to inform the user of queries done in the past. For instance, when they come back in future semesters to scrape new repositories containing course assignments. 

### Scraping Phase

Once the setup phase is complete, the user will be prompted with `Query (or @q to quit)? `. Here, the user should enter a query that is unique to the assignment of interest. This query will be passed in to search *code* on GitHub with the specified `language`. 

Once the results for the search are collected, the scraper will begin to "preview" the search results to the user one at a time. After displaying the beginning of the file, the user will need to press `Enter` in order to continue scrolling through the file (somewhat like the `less` Unix command). The preview will highlight lines of the previewed result in green that contain the query. The scraper **will not preview** results that belong to repositories that are listed in `records.txt`. This includes repositories that are discovered in the current scrape, so a user may notice the `x` in the displayed line `[INFO] : Previewing file x/y` go faster than one at a time as repositories (and potentially corresponding future search results) are downloaded.

Once a user has determined if the previewed result is a match for an assignment, type `y` and press `Enter`. If the user has determined that the result is not a match, type `n` and press `Enter`. If user does not want to see any more previewed results for the most recent query, type `q` and press `Enter`. If the user types anything else, it will be ignored and the preview will keep scrolling.

If the user reaches the end of a preview by scrolling through it with `Enter`, they will be forced to select `y` or `n` before moving to the next result to preview.

Once the user has previewed all the search results for a query, they will be prompted again for another query (or to quit).

### What happens when a user say yes to a preview?

The repository will be downloaded to a folder named `owner_repository` inside `collection_root` and `records.txt` is appropriately updated. If `raise_issue = true`, then an issue is raised on the repository. If `extra_directory` is specified, then a folder is created as described [above](#what-is-extra_directory).

If the user says a result is not a match, *other results from that repository will still be shown* in future previews if they are part of the search results. 

## Debugging the Scraper

The scraper also provides a detailed log in a file called `.github_scraper.log` in `collection_root`. By default, the scraper will append to the log, so if the file gets too large and unwieldy, the user can simply delete the file. The log's primary intention is for diagnosing API related issues in case of API changes in the future.

## Additional Notes

* It is possible that some repositories cannot be downloaded because they are too large. These should be manually investigated and one can use [this tool](https://download-directory.github.io/) to download a particular subfolder of a repository. 

## Potential Upgrades

* One nicety for users that could be added is to add a "keep" or "maybe" option when previewing a search result. At the moment, responding `n` in preview mode does do this. With the addition of this new option, `n` would act similarly to `y` in that repositories where a search record has been rejected will not be shown in future previews. The new option would just keep repositories in for future previews after responding with the new option to a preview. We think this could help a user go more quickly through previews.
* One possible optimization one could make is to download repositories in a separate thread. That way, users can go to preview the next search record while the download occurs in the background. However, one will need to take care that the user is not asked to preview a record that is currently part of the repository that is being downloaded since it may not be considered downloaded yet. One possible solution to this is to sort the collected records to preview by the owner and repository so that those can be skipped in a batch while the repository download is occuring in the background. 
* Move TOML scraping to utilize a dataclass versus constants and default dictionary.

## Authors

* [Chami Lamelas](https://sites.google.com/brandeis.edu/chamilamelas) 
* [Eitan Joseph](https://github.com/EitanJoseph)

## Changelog

### 7.28.2023

Added `custom_file` and `file_filter` capabilities to delete certain files from repositories that would be useless (e.g. binaries, Valgrind output).

### 5.1.2023

Added `requirements.txt`.

### 4.23.2023

Added displayed message when query yielded no records to preview.
Updated README with more information about rate limit violations.

### 3.7.2023

Add support for ~ in paths (ROOT, EXTRA_DIRECTORY).

### 3.1.2023

Major updates for spring 2023 use in Tufts COMP 15 including: 
- Introduced concept of collection root and organized records so previously downloaded repositories are not previewed again.
- Scrolling is done by default.
- Improved UI that allows for quitting previews for a query.
- Improved logging.
- Overall code refactoring.

### 1.14.2023

Used in Tufts COMP 15 in fall 2022. Planned for use in future semesters. First version moved to course repo.

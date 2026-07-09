# Gsheet Helper

As a Microsoft Office elitest, I am happy to debate why Excel is the superior product to Google Sheets. Despite the obvious superiority of Microsoft's offering, the reality is that Google Sheets is free and highly accessible. As such, its use has become prolific, used by students, freelancers, and corporate professionals around the world. 

As a data professional, most of my work is executed in Python, and sharing these results to external stakeholders can be challening. The ubiquity of Google Sheets makes it a powerful medium for sharing these analyses. Core functionality includes:
    1. Creating new Google Sheet Workbooks
    2. Sharing Workbooks
    3. Reading the contents of a Workbook (either a full tab, or a subset of data within the tab)
    4. Writing a pandas dataframe to a tab in an existing Workbook 

This class is not intended to be a cure-all for every possible use case of Google Sheets; Google provides a [full service API](https://developers.google.com/workspace/sheets/api/guides/concepts), on which this library is based. 

Much of the functionality in this library is highly duplicitive of existing libraries (e.g. [gsheets](https://github.com/xflr6/gsheets), Burnash's [gspread](https://github.com/burnash/gspread)). Unfortunately, as of the time of writing this, Burnash's `gspread` library is in need of a maintaner and cannot be relied upon for updates. 

This, in conjunction with some professional needs in my current role, providded my the impetuous to explore the Google API and create my own solution. 
----

# Installation

This package requires Python 3.10+ and is currently only intended for use as a local package. 

To install:

1. First clone the repo from github
```
$ cd ~/<local_repo_location>/
$ git clone <REPO_URL>
```

2. pip install the package locally
```
# Activate your virtual environment here, if desired. e.g. $ conda activate .venv

$ cd ~/<local_repo_location>/gsheet_helper
$ pip install -e .
```

This will also install google-api-python-client and its dependencies, notably httplib2 and oauth2client, as required dependencies.

# Quickstart
1. Get your Google Project Credentials
> Log into the [Google Developers Console](https://console.cloud.google.com) the Google account you wish to use to read and write Google Sheets. 
> Create (or select) a `project` and enable the Drive API and Sheets API.
> Go to the Credentials for your project and create New credentials > OAuth client ID > of type Other. In the list of your OAuth 2.0 client IDs click Download JSON for the Client ID you just created. Save the file as `credentials.json` within a `secrets/` folder in the `gsheet_helper` repository. 
> Once you have written `credentials.json` to the `gsheet_helper/secrets/` folder, you will need to create your `token.json` file, which is how Google will validate that your account has given access to the APIs requested in the project. 

2. Activate the virtual environment 
```
$ conda activate .venv
```
3. From the Terminal, run the following: 
Note that if credentials `--creds <PATH_TO_CREDENTIALS_JSON>` is an optional parameter -- if left blank, it will assume that `credentials.json` can be found in the standard location of `gsheet_helper/secrets`. If credentials are stored elsewhere, you will need to provide the full path.

```
$ gsheet_helper setup_auth --creds <PATH_TO_CREDENTIALS_JSON>
```

Your web browser will be opened, asking you to log in with your Google account to authorize this client read access to all its Google Drive files and Google Sheets.
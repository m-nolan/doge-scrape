# DOGE Data Scraper

# Introduction
The U.S. Dept. of Government Efficiency (DOGE) recently started posting records of the federal contracts they've cut, leases they've cut, and properties they've sold. The data is currently available on their website at this address: https://doge.gov/savings

To ease inspection and analysis, I wrote this Python script to scrape the api endpoints used to populate this website and save out DOGE's records as csv table files. The contract and property record files are available in this git repository under `/data/`. The scraping script used to download/update them is `doge-scrape.py`.

# Installation
To run this script, please clone the directory.

Change into the directory.

Install dependencies with
```pip install -r requirements.txt```


run the scraper with the following command:
```python doge-scrape.py```

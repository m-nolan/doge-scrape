# DOGE Data Scraper

# Introduction
The U.S. Dept. of Government Efficiency (DOGE) recently started posting records of the federal contracts they've cut, leases they've cut, and properties they've sold. The data is currently available on their website at this address: https://doge.gov/savings

To ease inspection and analysis, I wrote this python script to scrape the api endpoints used to populate this website and save out DOGE's records as csv table files. The contract and property files are available on this git repository, as well as the scraping script used to download them.

# Installation
To run this script, please clone the directory and run the scraper with the following command:
```python doge-scrape.py```

### Dependencies
- bs4
- numpy
- pandas
- validators
- tqdm
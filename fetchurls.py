import requests

from urllib.parse import urlparse, parse_qs
import os


contractdir = "contracts/"
os.makedirs(contractdir, exist_ok=True)

def find_filename(url):
	parsed = urlparse(url)
	qs = parse_qs(parsed.query)
	if "agencyID" not in qs:
		print(f"Dropping line: {qs}")
		return(None)
	else:
		basefilename = f"{qs['agencyID']}_{qs['PIID']}_{qs['modNumber']}"
		return(basefilename)

with open("url_list.txt", "r") as infile:
	url_list = infile.read().splitlines()
	
print(f"{len(url_list):,} URLs found.")

needed_dict = {}

for url in url_list:
	basefilename = find_filename(url)
	if basefilename:
		if not os.path.exists(contractdir + basefilename):
			needed_dict[url] = basefilename
		
print(f"{len(needed_dict)} URLs needed to be downloaded")


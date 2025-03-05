import requests
from tqdm import tqdm

# import asyncio
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs
import os


max_workers = 40
contractdir = "contracts/"
os.makedirs(contractdir, exist_ok=True)

async def fetch_a_file(url, basefilename):
    async with asyncio.TaskGroup() as tg:
        r = requests.get(url)
        if not r.ok:
            print(f"!!!!!")
            return
        else:
            with open(contractdir + basefilename, "wb") as outfile:
                outfile.write(r.content)
            print("+")
            return


def concurrent_fetch_a_file(url, basefilename):
    r = requests.get(url)
    if not r.ok:
        print(f"!!!!!")
        return
    else:
        with open(contractdir + basefilename, "wb") as outfile:
            outfile.write(r.content)
#@        print("+")
        return



def find_filename(url):
	parsed = urlparse(url)
	qs = parse_qs(parsed.query)
	if "agencyID" not in qs:
		print(f"Dropping line: {qs}")
		return(None)
	else:
		basefilename = f"{qs['agencyID'][0]}_{qs['PIID'][0]}_{qs['modNumber'][0]}"
		return(basefilename)

if __name__ == "__main__":
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

    # for url in needed_dict:
        # basefilename = needed_dict[url]
        # asyncio.run(fetch_a_file(url, basefilename))


    with ThreadPoolExecutor(max_workers=max_workers) as e:
        for url in tqdm(needed_dict):
            basefilename = needed_dict[url]
            e.submit(concurrent_fetch_a_file(url, basefilename))

import pandas as pd
import requests as req
import validators

from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm

data_key_dict = { # match on the 'id' field
    'entity_id': 'UEINumber',
    'entity_name': 'vendorName',
    'entity_dba': 'vendorDoingAsBusinessName',
    'cage_code': 'cageCode',
    'entity_street': 'vendorStreet',
    'entity_street_2': 'vendorStreet2',
    'entity_city': 'vendorCity',
    'entity_state': 'vendorState',
    'entity_zip': 'vendorZip',
    'entity_county': 'vendorCountry',
    'entity_county_disp': 'vendorCountryForDisplay',
    'entity_phone': 'vendorPhone',
    'entity_fax': 'vendorFax',
    'entity_congressional_district': 'vendorCongressionalDistrict',
    'product_service_code': 'productOrServiceCode',
    'product_service_desc': 'productOrServiceCodeDescription',
    'principal_naics_code': 'principalNAICSCode',
    'principal_naics_desc': 'NAICSCodeDescription',
}

def scrape_doge():
    doge_data_url = 'https://doge.gov/api/receipts/overview'
    r = req.get(doge_data_url)
    data_json = r.json()
    contract_df = pd.DataFrame(data_json['contracts'])
    property_df = pd.DataFrame(data_json['leases'])
    return contract_df, property_df

def parse_fpds_html(fpds_soup):
    data_dict = {}
    for k, qk in data_key_dict.items():
        data_dict[k] = fpds_soup.find('input',id=qk).get('value',default=None)
    data_dict['Description of Requirement'] = fpds_soup.find('textarea'
        ,id='descriptionOfContractRequirement').get('text',default=None)
    return data_dict

def extend_contract_data(contract_df):
    # lots of extra information on the fpds page. Takes a few seconds per item,
    # so this should be rewritten to avoid re-scraping.
    data_dict_list = []
    for fpds_link in tqdm(contract_df.fpds_link.values):
        if validators.url(fpds_link):
            r = req.get(fpds_link)
            data_dict_list.append(parse_fpds_html(BeautifulSoup(r.content)))
        else:
            data_dict_list.append({k: None for k, _ in data_key_dict.items()})
    return pd.concat([contract_df,pd.DataFrame(data_dict_list)],axis=1)

def clean_loc_str(loc):
    if ', ' in loc:
        city, state = loc.split(', ')
    else:
        city, state = None, None
    return city, state

def process_prop_data(property_df):
    property_df['city'], property_df['state'] = zip(*[clean_loc_str(loc) for loc in property_df['location']])
    return property_df

def save_doge_data(contract_df,property_df):
    # dtime_str = datetime.strftime(datetime.now(),'%Y%m%d%H%M%S')
    contract_df.to_csv(f'./data/doge-contract.csv',index=False)
    property_df.to_csv(f'./data/doge-property.csv',index=False)

def main():
    contract_df, property_df = scrape_doge()
    contract_df = extend_contract_data(contract_df)
    property_df = process_prop_data(property_df)
    save_doge_data(contract_df,property_df)

if __name__ == '__main__':
    main()
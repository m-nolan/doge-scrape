import numpy as np
import os
import pandas as pd
import requests as req
import validators

from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm

data_key_dict = { # match on the 'id' field
    'award_agency': 'agencyID',
    'award_procurement_id': 'PIID',
    'award_modification_num': 'modNumber',
    'ref_idv_agency': 'idvAgencyID',
    'ref_idv_procurement_id': 'idvPIID',
    'ref_idv_modification_num': 'idvModNumber',
    'date_signed': 'signedDate',
    'date_effective': 'effectiveDate',
    'date_complete': 'awardCompletionDate',
    'date_ult_complete_est': 'estimatedUltimateCompletionDate',
    'date_solicitation': 'solicitationDate',
    'amount_obligated': 'obligatedAmount',
    'amount_obligated_total': 'totalObligatedAmount',
    'amount_base_exercised_options': 'baseAndExercisedOptionsValue',
    'amount_base_exercised_options_total': 'totalBaseAndExercisedOptionsValue',
    'amount_ultimate': 'ultimateContractValue',
    'amount_ultimate_total': 'totalUltimateContractValue',
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

def safe_load_csv(filepath):
    return pd.read_csv(filepath) if os.path.exists(filepath) else pd.DataFrame([])

def load_pre_data():
    pre_contract_df = safe_load_csv('./data/doge-contract.csv')
    pre_property_df = safe_load_csv('./data/doge-property.csv')
    return pre_contract_df, pre_property_df

def scrape_doge():
    doge_data_url = 'https://doge.gov/api/receipts/overview'
    r = req.get(doge_data_url)
    data_json = r.json()
    contract_df = pd.DataFrame(data_json['contracts'])
    property_df = pd.DataFrame(data_json['leases'])
    property_df['sq_ft'] = [float(str(a).replace(',','')) if a is not None else None for a in property_df['sq_ft']]
    property_df['value'] = property_df['value'].astype(float)
    return contract_df, property_df

def parse_fpds_html(fpds_soup):
    data_dict = {}
    for k, qk in data_key_dict.items():
        element = fpds_soup.find('input',id=qk)
        data_dict[k] = element.get('value',default=None) if element is not None else None
        if 'amount' in k and data_dict[k] is not None:
            data_dict[k] = float(str(data_dict[k]).replace('$','').replace(',',''))
    data_dict['requirement_desc'] = fpds_soup.find('textarea'
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
    return pd.concat([contract_df.reset_index().drop('index',axis=1),pd.DataFrame(data_dict_list)],axis=1)

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

def update_doge_data():
    datetime_scrape = datetime.strftime(datetime.now(),'%Y-%m-%d-%H%M')
    pre_contract_df, pre_property_df = load_pre_data()
    contract_df, property_df = scrape_doge()
    new_contract_df = pd.concat([pre_contract_df,contract_df])[contract_df.columns].drop_duplicates(keep=False)
    new_property_df = pd.concat([pre_property_df,property_df])[property_df.columns].drop_duplicates(keep=False)
    new_contract_df = extend_contract_data(new_contract_df)
    new_contract_df['datetime_scrape'] = datetime_scrape
    new_property_df = process_prop_data(new_property_df)
    new_property_df['datetime_scrape'] = datetime_scrape
    contract_df = pd.concat([pre_contract_df,new_contract_df])
    # property_df = pd.concat([pre_property_df,new_property_df])
    return contract_df, property_df

def main():
    contract_df, property_df = update_doge_data()
    save_doge_data(contract_df,property_df)

if __name__ == '__main__':
    main()
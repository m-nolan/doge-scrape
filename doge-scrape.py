import io
import os
from datetime import datetime
from time import sleep

import pandas as pd
import requests as req
import validators
from bs4 import BeautifulSoup
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
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
    df = pd.read_csv(filepath) if os.path.exists(filepath) else pd.DataFrame([])
    if 'uploaded_dt' in df.keys():
        df['uploaded_dt'] = pd.to_datetime(df['uploaded_dt'])
    return df

def load_pre_data():
    pre_contract_df = safe_load_csv('./data/doge-contract.csv')
    pre_grant_df = safe_load_csv('./data/doge-grant.csv')
    pre_property_df = safe_load_csv('./data/doge-property.csv')
    return pre_contract_df, pre_grant_df, pre_property_df

def configure_driver():
    op = Options()
    op.add_argument('-headless')
    return Firefox(options=op)

def open_tables(driver):
    buttons = driver.find_elements(By.XPATH,"//*[contains(text(), 'View All ')]")
    [b.click() for b in buttons]
    return driver

def scrape_doge(driver):
    doge_data_url = 'https://doge.gov/savings'
    driver.get(doge_data_url)
    sleep(2)
    driver = open_tables(driver)
    table_list = driver.find_elements(By.XPATH,"//table")
    contract_df = pd.read_html(io.StringIO(table_list[0].get_attribute('outerHTML')))[0]
    link_cell_list = table_list[0].find_elements(By.XPATH,".//tr/td[4]")
    for idx, lc in enumerate(link_cell_list):
        ac = lc.find_elements(By.TAG_NAME,'a')
        contract_df.loc[idx,'Link'] = None if len(ac) == 0 else ac[0].get_attribute('href')
    grant_df = pd.read_html(io.StringIO(table_list[1].get_attribute('outerHTML')))[0]
    property_df = pd.read_html(io.StringIO(table_list[2].get_attribute('outerHTML')))[0]
    return contract_df, grant_df, property_df

def dollar_str_to_float(dstr):
    return float(dstr.replace('$','').replace(',',''))

def area_str_to_int(astr):
    return int(astr.replace(',',''))

def safe_to_dt(dtstr):
    try:
        dt = pd.to_datetime(dtstr)
    except:
        dt = None
    return dt

def df_row_diff(old_df,new_df):
    return pd.concat([old_df,new_df])[new_df.columns].drop_duplicates(keep=False)

def clean_stub_df(df):
    df.columns = [k.lower().replace(' ','_') for k in df.keys()]
    # in-column value replacement
    if 'value' in df.keys():
        df['value'] = [dollar_str_to_float(ds) for ds in df['value'].values]
    if 'annual_lease' in df.keys():
        df['annual_lease'] = [dollar_str_to_float(ds) for ds in df['annual_lease'].values]
    if 'uploaded_on' in df.keys():
        df['uploaded_dt'] = [safe_to_dt(dts) for dts in df['uploaded_on'].values]
    # column splitting and replacement
    if 'location' in df.keys():
        loc_part_list = [loc.split(', ') for loc in df['location'].values]
        for idx, loc_part_tup in enumerate(loc_part_list):
            city_pred = len(loc_part_tup[1]) == 2
            df.loc[idx,'city'] = loc_part_tup[0]    # city always first
            df.loc[idx,'state'] = loc_part_tup[1] if city_pred else None
            if len(loc_part_tup) > 2:
                df.loc[idx,'agency'] = loc_part_tup[2] if city_pred else loc_part_tup[1]
    return df

def parse_fpds_html(fpds_soup):
    data_dict = {}
    for k, qk in data_key_dict.items():
        element = fpds_soup.find('input',id=qk)
        data_dict[k] = element.get('value',default=None) if element is not None else None
        if 'amount' in k and data_dict[k] is not None:
            data_dict[k] = float(str(data_dict[k]).replace('$','').replace(',',''))
    req_desc_element = fpds_soup.find('textarea',id='descriptionOfContractRequirement')
    data_dict['requirement_desc'] = None if req_desc_element is None else req_desc_element.get('text',default=None)
    return data_dict

def extend_contract_data(contract_df):
    data_dict_list = []
    rh = req.utils.default_headers()
    # this takes about 2s per iteration. Speedup without DOSing the FPDS server?
    for fpds_link in tqdm(contract_df.link.values):
        if validators.url(fpds_link):
            r = req.get(fpds_link,headers=rh)
            data_dict_list.append(parse_fpds_html(BeautifulSoup(r.content,features="lxml")))
        else:
            data_dict_list.append({k: None for k, _ in data_key_dict.items()})
    return pd.concat([contract_df.reset_index().drop('index',axis=1),pd.DataFrame(data_dict_list)],axis=1)

def save_doge_data(contract_df,grant_df,property_df):
    contract_df.to_csv(f'./data/doge-contract.csv',index=False)
    grant_df.to_csv(f'./data/doge-grant.csv',index=False)
    property_df.to_csv(f'./data/doge-property.csv',index=False)

def update_doge_data():
    datetime_scrape = datetime.strftime(datetime.now(),'%Y-%m-%d-%H%M')
    print('configuring headless chrome driver...')
    driver = configure_driver()
    print('loading current data...')
    pre_contract_df, pre_grant_df, pre_property_df = load_pre_data()
    print('scraping new data...')
    stub_contract_df, stub_grant_df, stub_property_df = scrape_doge(driver)
    stub_contract_df, stub_grant_df, stub_property_df = [clean_stub_df(df) for df in [stub_contract_df, stub_grant_df, stub_property_df]]
    new_contract_df, new_grant_df, new_property_df = [
        df_row_diff(pre_df,stub_df) for pre_df, stub_df in zip(
            [pre_contract_df,pre_grant_df,pre_property_df],[stub_contract_df, stub_grant_df, stub_property_df]
        )
    ]
    print('extending contract table with FPDS data...')
    new_contract_df = extend_contract_data(new_contract_df)
    new_contract_df['dt_scrape'] = datetime_scrape
    new_grant_df['dt_scrape'] = datetime_scrape
    new_property_df['dt_scrape'] = datetime_scrape
    contract_df = pd.concat([pre_contract_df,new_contract_df])
    grant_df = pd.concat([pre_grant_df,new_grant_df])
    property_df = pd.concat([pre_property_df,new_property_df])
    return contract_df, grant_df, property_df

def main():
    contract_df, grant_df, property_df = update_doge_data()
    save_doge_data(contract_df,grant_df,property_df)

if __name__ == '__main__':
    main()
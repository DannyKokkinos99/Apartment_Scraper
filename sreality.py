from selenium import webdriver
import time
from bs4 import BeautifulSoup
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import sqlite3
from pathlib import Path
import math
import gspread

def sreality():
    BASE = "https://www.sreality.cz"
    RENT = "https://www.sreality.cz/hledani/pronajem/byty?region=Brno&velikost=2%2Bkk,2%2B1,3%2Bkk&plocha-od=50&plocha-do=10000000000&cena-od=0&cena-do=23000&region-id=5740&region-typ=municipality&k-nastehovani=ihned"
    CONDITIONS = ["pračk", "myčk"]  #Maximum of 2 conditions
    DATABASE = Path("database.db")
    QUERIES = Path("queries.sql")
    BAD_AREAS = ["Zábrdovice", "Řečkovice", "Bystrc"] #areas you want to exclude from your search
    SPREADSHEET_ID = "1v54j8oOHO9mchR_Akf05NE3WiLIEeosA9fnLOYQq3iw" #spreadsheet ID can be found in the url
    SERVICE_ACCOUNT = "service_account.json" #Service account token
    UPDATE_DATE = ["Včera", "Dnes"]
    # get queries
    with open(
        QUERIES, "r", encoding="UTF-8"
    ) as file:  # import SQL queries
        queries = file.read().split(";")
    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome()
    # Create connection to database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # run selenium
    html_content = get_page_html(RENT,driver)
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    listings = soup.findAll('div', class_='property ng-scope')
    num_listings = int(soup.findAll('span',class_='numero ng-binding')[1].text)
    pages = math.ceil(num_listings / len(listings)) + 1
    counter_1 = counter_2 = 0
    for page in range(1,pages+1): #for each page in pages
        page_q = f"&strana={page}"
        url = RENT + page_q
        print(url)
        html_content = get_page_html(url,driver)
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = soup.findAll('div', class_='property ng-scope')
        for listing in listings: #for each listing
            title = ''
            address = ''
            url = ''
            phone = ''
            description = ''
            title = listing.find('span', class_='name ng-binding').text
            address = listing.find('span', class_='locality ng-binding').text
            url = BASE + listing.find("a")["href"]
            print(url)
            html_content = get_page_html(url,driver)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            #Extracts the updated status
            temp = soup.findAll('strong', class_='param-value')[3].text
            lines = temp.split('\n')
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            updated_status = '\n'.join(cleaned_lines)
            phone = soup.find('div', class_='contacts').find('a', class_ = 'value final ng-binding ng-hide')['href'].replace('tel:', '').replace('+420', '')
            description = soup.find('div', class_='description ng-binding').text
            #checks white goods
            conditions_state = check_white_goods(CONDITIONS, description)
            #if no white goods
            if conditions_state[1] == 0:
                print("Apartment has no white goods")
                continue
            #check updated date
            if not check_condition(UPDATE_DATE, updated_status):
                print("Apartment not updated recently")
                continue
            #checks area
            if check_condition(BAD_AREAS, address):
                print("Apartment in bad area")
                continue
            #determine which table to add it to
            if "2+kk" in title or "1+1" in title:
                apartment_num = 1
            elif "3+kk" in title or "2+1" in title:
                apartment_num = 2
            else:
                print("Apartmen wrong number of bedrooms")
                continue
            #add listing to database
            table_name = f"apartments_{apartment_num}_bedroom"
            # table_name = f"apartments_{apartment_num}_bedroom_Ostrava"
            apartment = [address, url, conditions_state[0],conditions_state[1] , phone]
            create_table(cursor, queries[0], table_name)
            if insert_data(conn,cursor, queries[1],table_name, apartment) is False: #if listing in database skips adding it to google sheet
                print("Apartment already in table")
                continue
            #counters
            if apartment_num == 1:
                counter_1 += 1
            if apartment_num == 2:
                counter_2 += 1
            #add data to google sheet
            add_to_google_sheet(SERVICE_ACCOUNT, SPREADSHEET_ID, apartment, apartment_num)
    print(f'{counter_1} new 1-Bedroom apartments added to google sheet')
    print(f'{counter_2} new 2-Bedroom apartments added to google sheet')

    driver.close()
    cursor.close()


def get_page_html(url,driver):
    driver.get(url)
    time.sleep(2)
    html_content = driver.page_source
    return html_content


def check_white_goods(conditions, description):
    temp = []
    for condition in conditions:
        if condition in description:
            temp.append(1)
        else:
            temp.append(0)
    return temp


def check_condition(conditions, something):
    if conditions == []: # used when dates are not restricted
        return True
    for condition in conditions:
        if condition.lower().replace(" ", "") in something.lower().replace(" ", ""):
            return True
    return False


def create_table(cursor, query, table_name):
    table = query.format(table_name)
    cursor.execute(table)  # Create table


def insert_data(conn, cursor, query, table_name,data):
    query_formated = query.format(table_name)
    try:
        
        data = (
            data[0], #address
            data[1], #URL
            data[2], #Condition 1
            data[3], #Condition 2
            data[4], # phone number
        )
        cursor.execute(query_formated, data)  # Insert data into table
        conn.commit()
        print(f"Adding {data[0]} to {table_name}")
        return True
    except sqlite3.IntegrityError:
        return False

def add_to_google_sheet(service_account,spreadshet_id,data,apartment_num):
    gc = gspread.service_account(service_account)
    sheets = gc.open_by_key(spreadshet_id)

    worksheet = sheets.get_worksheet(apartment_num)
    row = len(worksheet.col_values(1)) + 1  # Get length of used rows
    worksheet.update_acell(f"A{row}", '=TEXT(NOW(), "dd/MM")')
    # Add address and hyperlink
    worksheet.update_acell(
        f"B{row}", f'=HYPERLINK("{data[1]}", "{data[0]}")'
    )  

    row_data = ["No", "No", "No", "No", ""]
    if data[2] == 1:
        row_data[0] = "Yes"
    if data[3] == 1:
        row_data[1] = "Yes"

    row_data.append(data[4])  # adds phone number
    ranges = f"C{row}:H{row}"
    worksheet.update(
        range_name=ranges, values=[row_data]
    )  # Selects the list options
    print(f"Added listing to {apartment_num}_Bedroom_apartment in google sheet")

sreality()
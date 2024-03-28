'''This module is used to extract real estate from listings from the bravis website. 
It then adds it to a local database all unique listings are automatically added
to a google sheet for ease of use.No more manually searching for properties in Czech!
'''
from datetime import datetime
import sqlite3
import math
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import gspread

# Bravis
DATABASE = Path("database.db")
QUERIES = Path("queries.sql")
ROOMS = [2, 3]  # cannot be changed yet must make change to index in loop first
CONDITIONS = ["dishwasher", "washing machine"]  #Maximum of 2 conditions
CHECK_DATE = datetime(2024, 5, 1)  # Select Move in date
SPREADSHEET_ID = "1v54j8oOHO9mchR_Akf05NE3WiLIEeosA9fnLOYQq3iw" #spreadsheet ID can be found in the url
SERVICE_ACCOUNT = "service_account.json" #Service account token
RENT = "https://www.bravis.cz/en/for-rent"
BASE = "https://www.bravis.cz/en/"
LISTINGS_PER_PAGE = 21 #number of listings per page
BAD_AREAS = ["Zábrdovice"] #areas you want to exclude from your search

def main():
    """Does everything """
    # Connecting to database
    with open(
        QUERIES, "r", encoding="UTF-8"
    ) as file:  # import SQL queries
        queries = file.read().split(";")
    # Check how many pages exist
    response = requests.get(RENT)
    page_numbers = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        details = soup.find("div", class_="more").find_all("li")
        for detail in details:
            number_of_bedrooms = int(detail.get_text()[0])
            if number_of_bedrooms not in ROOMS:
                continue
            number_of_listings = int(detail.get_text().split("(")[-1].split(")")[0])
            page_number = math.ceil(number_of_listings / LISTINGS_PER_PAGE)
            page_numbers.append(page_number)

    for i, n in enumerate(ROOMS):  # for different number of rooms
        added_counter = 0
        rent = f"rent-{n}-plus-kk-{n}-plus-1"
        for p in range(page_numbers[i]):  # for each page
            print(f"Compiling data for {n-1}-Bedroom apartments")
            page_number = f"?s={p+1}-order-0"
            url = BASE + rent + page_number
            response = requests.get(url)
            if response.status_code == 200:

                soup = BeautifulSoup(response.text, "html.parser")
                list_item = soup.find("div", class_="initemslist")
                items = list_item.find_all("div", class_="item")
                for _, item in enumerate(items):  # for each listing on the page
                    conditions_state = [0 for _ in range(len(CONDITIONS))]
                    address = item.find("span", class_="ico location s14").text
                    url = BASE + item.find("a")["href"]
                    response = requests.get(url)
                    if response.status_code == 200:
                        inner_soup = BeautifulSoup(response.text, "html.parser")

                        phone = (
                            inner_soup.find("a", class_="phone")
                            .text.replace(" ", "")
                            .replace("420", "")
                        )
                        furniture = inner_soup.find("div", class_="furniture")
                        strongs = furniture.findAll("strong")

                        # if item is not Reserved
                        gallery = inner_soup.find("div", class_="newgallery").text.strip()
                        if "Reserved" in gallery or "Pre-reserved" in gallery:
                            continue

                        # date after specific date
                        temp = gallery.replace("Available", "").replace(" ", "").split(".")
                        date = datetime(int(temp[2]), int(temp[1]), int(temp[0]))
                        if date < CHECK_DATE:
                            continue
                        # if located in bad area
                        flag = 0
                        for area in BAD_AREAS:
                            if area in address:
                                flag = 1
                                continue
                        if flag == 1:
                            continue
                        for _, s in enumerate(
                            strongs
                        ):  # checking if furniture in wanted furniture list
                            piece_of_furniture = s.text.lower()
                            for i, con in enumerate(CONDITIONS):
                                if piece_of_furniture == con.lower():
                                    conditions_state[i] = 1

                        # Add new listings to database
                        conn = sqlite3.connect(DATABASE)
                        cursor = conn.cursor()
                        table_name = f"apartments_{n-1}_bedroom"

                        create_table = queries[0].format(table_name)
                        insert_data = queries[1].format(table_name)
                        cursor.execute(create_table)  # Create table

                        try:
                            data = (
                                address,
                                url,
                                conditions_state[0],
                                conditions_state[1],
                                phone,
                            )
                            cursor.execute(insert_data, data)  # Insert data into table
                            conn.commit()
                            added_counter += 1
                            conn.close()
                        except sqlite3.IntegrityError:
                            conn.close()
                            continue

                        # add to google sheet
                        gc = gspread.service_account(SERVICE_ACCOUNT)
                        sheets = gc.open_by_key(SPREADSHEET_ID)

                        worksheet = sheets.get_worksheet(n-1)
                        row = len(worksheet.col_values(1)) + 1  # Get length of used rows
                        worksheet.update_acell(f"A{row}", '=TEXT(NOW(), "dd/MM")')
                        worksheet.update_acell(
                            f"B{row}", f'=HYPERLINK("{url}", "{address}")'
                        )  # Add address and hyperlink

                        row_data = ["Maybe", "Maybe", "No", "No", ""]
                        if conditions_state[0] == 1:
                            row_data[0] = "Yes"
                        if conditions_state[1] == 1:
                            row_data[1] = "Yes"

                        row_data.append(phone)  # adds phone number
                        ranges = f"C{row}:H{row}"
                        worksheet.update(
                            range_name=ranges, values=[row_data]
                        )  # Selects the list options
        print(f"{added_counter} new {n-1}-bedrooms apartments added to table.")

    conn.close()
if __name__ == "__main__":
    main()
    print("Process complete!")

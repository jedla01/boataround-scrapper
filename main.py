from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlencode
import csv
import argparse
import requests
import time
import os
import re


def parse_price(text):
    try:
        group = re.search(r"([\d\.\,]+\s*)", text, re.UNICODE).group(1)
        return int(re.sub(r"\.|\,", "", group))
    except:
        return 0

def total_price(boat):
    sum = 0
    for item in ['transit_log', 'deposit_insurance']:
        if item not in boat:
            continue
        if boat[item] != 'NA':
            sum += parse_price(boat[item])
    if 'freecancel_price' in boat and boat["freecancel_price"] != 'NA':
        sum += parse_price(boat["freecancel_price"])
    elif 'partrefund_price' in boat and boat["partrefund_price"] != 'NA':
        sum += parse_price(boat["partrefund_price"])
    elif 'norefund_price' in boat and boat["norefund_price"] != 'NA':
        sum += parse_price(boat["norefund_price"])
    else:
        pass
    if sum == 0:
        return 'NA'
    return sum

query_params = {
    "destinations": "croatia",
    "checkIn": "2024-05-18",
    "checkOut": "2024-05-25",
    "category": "sailing-yacht",
    "cabins": "3",
    "price": "-2000",
    "year": "2012-",
    "sail": "rolling-mainsail",
    "services": "deposit-insurance",
    "sort": "priceUp"
}

features_dict = {
    "year": "year",
    "people": "people",
    "berths": "berths",
    "cabins": "cabins",
    "toilets": "toilets",
    "draught": "draught",
    "beam": "beam",
    "engine": "engine",
    "fuel_tank": "fuel tank",
    "water_tank": "water tank",
    "length": "length",
}

extras_dict = {
    "dinghy_engine": "dinghy engine",
    "flex_cancel": "flexible cancellation",
    "early_checkin": "early boat check-in",
    "skipper": "skipper",
    "hostess": "hostess",
    "pets": "pets onboard",
    "safety_net": "safety net",
    "paddle_board": "stand up paddle",
    "towels": "towels",
    "extra_linen": "extra bed linen",
    "transit_log": "transit log",
    "refund_deposit": "refundable security deposit",
    "deposit_insurance": "deposit insurance"
}

# Define the Chrome webdriver options
options = webdriver.FirefoxOptions()
options.add_argument("--headless") # Set the Chrome webdriver to run in headless mode for scalability

# By default, Selenium waits for all resources to download before taking actions.
# However, we don't need it as the page is populated with dynamically generated JavaScript code.
options.page_load_strategy = "none"
driver = webdriver.Firefox(options=options)
driver.implicitly_wait(5)
wait = WebDriverWait(driver, timeout=15)
wait_rating = WebDriverWait(driver, timeout=5)

base_URL = "https://www.boataround.com"

driver.get(f"{base_URL}/search?{urlencode(query_params)}")
quit_subscribe = wait.until(EC.visibility_of_element_located((By.XPATH, "/html/body/main/div[3]/section/div/i")))
quit_subscribe.click()

page_count = driver.find_element(By.XPATH, "//ul[@class='paginator__items']/li[4]/a").text

boat_links = []
boats = []

for page in range(1, int(page_count)+1):
    if page > 1:
        driver.get(f"{base_URL}/search?{urlencode(query_params)}&page={page}")
    time.sleep(2)
    items = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//section[@class='search-results-list']/ul/li/a")))
    boat_links.extend([item.get_attribute('href') for item in items])
    page+=1

for i in range(len(boat_links)):
    boat = {}
    boat["url"] = boat_links[i]
    # Collect boat details
    # driver.get('https://www.boataround.com/boat/bavaria-cruiser-46-kalev?checkIn=2024-05-11&checkOut=2024-05-18')
    driver.get(boat_links[i])
    time.sleep(2)

    # Boat name
    boat["name"] = wait.until(EC.visibility_of_element_located((By.XPATH, "/html/body/main/div[2]/div[3]/div/div[2]/div[1]/div[1]/div[1]/h1"))).text
    print(boat["name"])
    boat["marina"] = wait.until(EC.visibility_of_element_located((By.XPATH, "/html/body/main/div[2]/div[3]/div/div[2]/div[1]/div[1]/div[2]/div/button/span[2]"))).text
    boat["charter"] = wait.until(EC.visibility_of_element_located((By.XPATH, "//p[@class='reservation-box__header-charter']"))).text.split(":")[1].strip()
    try:
        boat["rating"] = wait_rating.until(EC.visibility_of_element_located((By.XPATH, "//div[@class='review-score-box']"))).text
    except:
        boat["rating"] = 0

    # Boat reservation
    reservations = wait.until(EC.visibility_of_all_elements_located((By.XPATH, "//div[contains(@class,'reservation-box__policies-row')]")))
    boat["norefund_price"] = 'NA'
    boat["freecancel_price"] = 'NA'
    boat["partrefund_price"] = 'NA'
    for reservation in reservations:
        cancel_policy = reservation.find_element(By.XPATH, ".//span[contains(@class, 'reservation-box__policy-cancel')]").text
        if 'Non-refundable' in cancel_policy:
            boat["norefund_price"] = reservation.find_element(By.XPATH, ".//span[contains(@class, 'price-box__price')]").text
        if 'Partially refundable' in cancel_policy:
            boat["partrefund_price"] = reservation.find_element(By.XPATH, ".//span[contains(@class, 'price-box__price')]").text
        if 'FREE cancellation' in cancel_policy:
            boat["freecancel_price"] = reservation.find_element(By.XPATH, ".//span[contains(@class, 'price-box__price')]").text

    # Boat info
    boat_info_ul = wait.until(EC.visibility_of_all_elements_located((By.XPATH, "//section[@class='boat-info-list']/ul/li")))
    for li in boat_info_ul:
        key = li.find_element(By.CLASS_NAME, "boat-info-list__key").text
        value = li.find_element(By.CLASS_NAME, "boat-info-list__value").text
        for x in features_dict:
            if features_dict[x] in key.lower():
                boat[x] = value

    services_extras = wait.until(EC.visibility_of_all_elements_located((By.XPATH, "//section[@class='extras-list']/label")))
    for label in services_extras:
        key = label.find_element(By.CLASS_NAME, "extra-item__heading").text
        value = label.find_element(By.CLASS_NAME, "extra-item__price").text
        for x in extras_dict:
            if extras_dict[x] in key.lower():
                boat[x] = value

    try:
        excluded_charges = wait.until(EC.visibility_of_all_elements_located((By.XPATH, "//div[contains(@class, 'excluded')]/div[contains(@class, 'extra-item')]")))
        for item in excluded_charges:
            key = item.find_element(By.CLASS_NAME, "extra-item__heading").text
            value = item.find_element(By.CLASS_NAME, "extra-item__price").text
            for x in extras_dict:
                if extras_dict[x] in key.lower():
                    boat[x] = value
    except:
        pass

    boats.append(boat)

data = []
for boat in boats:
    record = {
        "name": boat["name"],
        "marina": boat["marina"],
        "charter": boat["charter"],
        "rating": float(boat["rating"]),
        "norefund_price": parse_price(boat.get("norefund_price", "NA")),
        "partrefund_price": parse_price(boat.get("partrefund_price", "NA")),
        "freecancel_price": parse_price(boat.get("freecancel_price", "NA")),
        "transit_log": parse_price(boat.get("transit_log", "NA")),
        "refund_deposit": parse_price(boat.get("refund_deposit", "NA")),
        "deposit_insurance": parse_price(boat.get("deposit_insurance", "NA")),
        "total_price": total_price(boat),
        "year": boat.get("year", "NA"),
        "engine": boat.get("engine", "NA"),
        "people": boat.get("people", "NA"),
        "cabins": boat.get("cabins", "NA"),
        "toilets": boat.get("toilets", "NA"),
        "draught": boat.get("draught", "NA"),
        "beam": boat.get("beam", "NA"),
        "length": boat.get("length", "NA"),
        "fuel_tank": boat.get("fuel_tank", "NA"),
        "water_tank": boat.get("water_tank", "NA"),
        "url": boat["url"]
    }
    data.append(record)

keys = data[0].keys()

with open('boats.csv', 'w', newline='', encoding="utf8") as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(data)

time.sleep(2)
driver.quit()

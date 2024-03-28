## Introduction
This repository contains a script used to extract apartments or houses from Bravis real estate's website.
Main use for this script would be if you move to Brno Czechia and are looking for an apartment.
The listings are saved in a local database and each unique listing is added to a google sheet for inspection.
A different google sheet would have to be attached and a google service account JSON file needs to be created.

## Prerequisites
Code has been tested on python version 3.8.0

## Dependencies
There are 2 main methods for installing the dependencies

### 1. Install dependencies directly
1. Run "pip install -r requirements.txt"

### 2. Install dependencies using virtual environment
1. Open a terminal within the project folder
2. Run "pipenv install -r requirements.txt"
3. Select the correct interpreter

## How to use the script
1. Fill the initial parameters in main.py
2. Run the script
3. If configured correctly the listings will appear in the connected google sheet


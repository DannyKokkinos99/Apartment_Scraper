CREATE TABLE IF NOT EXISTS {} (
                    "Address"	TEXT UNIQUE,
                    "URL"	TEXT,
                    "Washing_Machine"	INTEGER,
                    "Dishwasher"	INTEGER,
                    "Phone_Number"	INTEGER,
                    PRIMARY KEY("URL")
);

INSERT INTO {} (Address, URL, Washing_Machine, Dishwasher, Phone_Number) VALUES (?, ?, ?, ?, ?);

SELECT COUNT(*) FROM {} WHERE URL = ?;




import os
import json
import gzip
import shutil
import logging
from random import randint
from datetime import datetime, timedelta
from appdirs import site_data_dir
from typing import Any, Dict, List




class Entry:

    def __init__(self, value: Any, expire_date: datetime):
        self.expire_date = expire_date
        self.value = value

    def is_expired(self):
        return datetime.now() > self.expire_date

    def to_dict(self) -> Dict:
        return {"value": self.value,
               "expire_date": self.expire_date.strftime("%Y.%m.%d %H:%M:%S")}

    @staticmethod
    def from_dict(dict: Dict):
        return Entry(dict['value'], datetime.strptime(dict['expire_date'], "%Y.%m.%d %H:%M:%S"))


class SimpleDB:

    def __init__(self, name: str, sync_period_sec:int = 5*60):
        self.sync_period_sec = sync_period_sec
        self.__name = name
        self.__directory = site_data_dir("simpledb", appauthor=False)
        self.__data = self.__load()
        self.__last_time_stored = datetime.now()
        logging.info("simple db: using " + self.filename + " (" + str(len(self.__data)) + " entries)")

    @property
    def filename(self):
        if not os.path.exists(self.__directory):
            logging.info("directory " + self.__directory + " does not exits. Creating it")
            os.makedirs(self.__directory)
        return os.path.join(self.__directory, self.__name + ".json.gz")

    def __len__(self):
        return len(self.__data)

    def keys(self) -> List:
        keys = set()
        for key in list(self.__data.keys()):
            entry = self.__data[key]
            if not entry.is_expired():
                keys.add(entry.value)
        return list(keys)

    def has(self, key) -> bool:
        return key in self.keys()

    def put(self, key: str, value: Any, ttl_sec: int = 1000*365*24*60*60):  # default ttl: 1000 years
        self.__data[key] = Entry(value, datetime.now() + timedelta(seconds=ttl_sec))
        if datetime.now() >= (self.__last_time_stored + timedelta(seconds=self.sync_period_sec)):
            self.__store()
            self.__last_time_stored = datetime.now()

    def get(self, key: str, default_value: Any = None):
        entry = self.__data.get(key, None)
        if entry is None or entry.is_expired():
            return default_value
        else:
            return entry.value

    def get_values(self):
        values = []
        for key in list(self.__data.keys()):
            entry = self.__data[key]
            if not entry.is_expired():
                values.append(entry.value)
        return values

    def delete(self, key):
        del self.__data[key]

    def clear(self):
        self.__data = {}
        self.__store()

    def __remove_expired(self):
        for key in list(self.__data.keys()):
            entry = self.__data[key]
            if entry.is_expired():
                del self.__data[key]

    def __load(self) -> Dict:
        if os.path.isfile(self.filename):
            with gzip.open(self.filename, "rb") as file:
                try:
                    json_data = file.read()
                    data = json.loads(json_data.decode("UTF-8"))
                    return {name: Entry.from_dict(data[name]) for name in data.keys()}
                except Exception as e:
                    logging.warning("could not load " + self.filename + " " + str(e))
        return {}

    def __store(self):
        try:
            self.__remove_expired()
        except Exception as e:
            logging.info("error occurred removing expired records " + str(e))

        tempname = self.filename + "." + str(randint(0, 10000)) + ".temp"
        try:
            data = {name: self.__data[name].to_dict() for name in self.__data.keys()}
            with gzip.open(tempname, "wb") as tempfile:
                tempfile.write(json.dumps(data, indent=2).encode("UTF-8"))
            shutil.move(tempname, self.filename)
        finally:
            os.remove(tempname) if os.path.exists(tempname) else None

    def __str__(self):
        return "\n".join([str(name) + ": " + str(self.__data[name].value) + " (ttl=" + self.__data[name].expire_date.strftime("%d.%m %H:%M") + ")" for name in self.__data.keys()])

    def __repr__(self):
        return self.__str__()
import os
import pickle
import shutil
import logging
from datetime import datetime, timedelta
from appdirs import site_data_dir
from dataclasses import dataclass
from typing import Any, Dict, List



@dataclass
class Entry:
    expire_date : datetime
    value: Any

    def is_expired(self):
        return datetime.now() > self.expire_date



class SimpleDB:

    def __init__(self, name: str, sync_period_sec:int = 5*60):
        self.sync_period_sec = sync_period_sec
        directory = site_data_dir("simpledb", appauthor=False)
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.__filename = os.path.join(directory, name + ".p")
        self.__data = self.__load()
        self.__last_time_stored = datetime.now()
        logging.info("simple db: using " + self.__filename + " (" + str(len(self.__data)) + " entries)")

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

    def put(self, key, value: Any, ttl_sec: int = 1000*365*24*60*60):  # default ttl: 1000 years
        self.__data[key] = Entry(datetime.now() + timedelta(seconds=ttl_sec), value)
        if datetime.now() > (self.__last_time_stored + timedelta(seconds=self.sync_period_sec)):
            self.__store()
            self.__last_time_stored = datetime.now()

    def get(self, key, default_value: Any = None):
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
        if os.path.isfile(self.__filename):
            with open(self.__filename, 'rb') as file:
                return pickle.load(file)
        return {}

    def __store(self):
        tempname = self.__filename + "." + str(range(10000)) + ".temp"
        try:
            self.__remove_expired()
        except Exception as e:
            logging.info("error occurred removing expired records " + str(e))
        try:
            with open(tempname, 'wb') as file:
                pickle.dump(self.__data, file)
            shutil.move(tempname, self.__filename)
        finally:
            os.remove(tempname) if os.path.exists(tempname) else None

    def __str__(self):
        return "\n".join([str(name) + ": " + str(self.__data[name].value) + " (ttl=" + self.__data[name].expire_date.strftime("%d.%m %H:%M") + ")" for name in self.__data.keys()])

    def __repr__(self):
        return self.__str__()
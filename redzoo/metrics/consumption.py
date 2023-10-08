import logging
from abc import ABC, abstractmethod
from time import sleep
from typing import Optional, List, Tuple
from random import randint
from datetime import datetime, timedelta
from redzoo.database.simple import SimpleDB




class AverageRecorder:

    def __init__(self, width_sec : int = 15):
        self.width_sec = width_sec
        self.__measures: List[Tuple[datetime, float]] = list()
        self.__value = 0
        self.__last_refresh = datetime.now()

    def put(self, measure: float):
        self.__measures.append((datetime.now(), measure))

    def __compact(self):
        compacted_measures = list()
        for date_measure_pair in list(self.__measures):
            time = date_measure_pair[0]
            measure = date_measure_pair[1]
            if time + timedelta(seconds=self.width_sec) > datetime.now():
                compacted_measures.append((time, measure))
        self.__measures = compacted_measures

    def __refresh_value(self):
        self.__compact()
        measures = [date_measure_pair[1] for date_measure_pair in self.__measures]
        if len(measures) > 0:
            self.__value = sum(measures) / len(measures)
        else:
            self.__value = 0

    def value(self) -> float:
        now = datetime.now()
        if self.__last_refresh + timedelta(seconds=self.width_sec) < now:
            self.__refresh_value()
            self.__last_refresh = now
        return self.__value


class HourRecorder:

    def __init__(self):
        self.time = datetime.strptime(datetime.now().strftime("%Y.%m.%d %H") + ":00:00", "%Y.%m.%d %H:%M:%S")
        self.__last_time_added = self.time
        self.__is_recording = False
        self.__width_secs = None
        self.__previous_measure = None
        self.__value = 0

    @property
    def value(self) -> float:
        return self.__value

    def put(self, measure: float):
        now = datetime.now()
        if self.__is_recording:
            elapsed_sec = (now - self.__last_time_added).total_seconds()
            self.__value += self.__previous_measure * (elapsed_sec / self.__width_secs)
        else:
            offset_seconds = (now - self.time).total_seconds()
            self.__width_secs = (60 * 60) - offset_seconds
            self.__is_recording = True
        self.__previous_measure = measure
        self.__last_time_added = now



class ConsumptionRecorder(ABC):

    def __init__(self, name: str):
        self.__name = name

    @abstractmethod
    def record(self, value: float):
        pass

    @abstractmethod
    def consumption_hour(self) -> float:
        pass

    def consumption_day(self, offset:int = 0) -> float:
        pass

    @abstractmethod
    def consumption_year(self) -> float:
        pass

    @abstractmethod
    def estimated_consumption_365_days(self) -> float:
        pass



class ConsumptionGaugeRecorder(ConsumptionRecorder):

    def __init__(self, name: str):
        self.day_series = SimpleDB(name + "_day_resolution", sync_period_sec=60)
        self.hour_series = SimpleDB(name + "_hour_resolution", sync_period_sec=60)
        self.hour_recorder = HourRecorder()
        self.average_recorder = AverageRecorder()
        super().__init__(name)

    def clear(self):
        self.day_series.clear()
        self.hour_series.clear()

    def record(self, current_value: float):
        if datetime.now() > (self.hour_recorder.time + timedelta(minutes=60)):
            recording_time = self.hour_recorder.time
            self.day_series.put(recording_time.strftime("%Y.%m.%d"), self.__aggregated_day_value(recording_time), ttl_sec=3 * 365 * 24 * 60 * 60)  # ttl: 3 years
            self.hour_recorder = HourRecorder()
        self.hour_recorder.put(current_value)
        self.hour_series.put(self.hour_recorder.time.strftime("%Y.%m.%d %H"), self.hour_recorder.value, ttl_sec=3 * 24 * 60 * 60)  # ttl: 72 hours
        self.average_recorder.put(current_value)

    def __aggregated_day_value(self, time: datetime) -> Optional[float]:
        time_hour_resolution = datetime.strptime(time.strftime("%Y.%m.%d") + " 00:00:00", "%Y.%m.%d %H:%M:%S")
        values = []
        for hour in range(23+1):
            hour_key = (time_hour_resolution + timedelta(hours=hour)).strftime("%Y.%m.%d %H")
            value = self.hour_series.get(hour_key, None)
            if value is not None:
                values.append(value)
        if len(values) > 0:
            return sum(values)
        else:
            return 0

    def consumption_current(self) -> float:
        return self.average_recorder.value()

    def consumption_hour(self, time: datetime = None) -> float:
        if time is None:
            return self.hour_recorder.value
        else:
            return self.hour_series.get(time.strftime("%Y.%m.%d %H"), 0)

    def consumption_day(self, offset:int = 0) -> float:
        first_hour = datetime.strptime((datetime.now() + timedelta(days=offset)).strftime("%Y.%m.%d") + " 00:00:00", "%Y.%m.%d %H:%M:%S")
        values = []
        for hour in range(0, 23+1):
            hour_key = (first_hour + timedelta(hours=hour)).strftime("%Y.%m.%d %H")
            value = self.hour_series.get(hour_key, None)
            if value is not None:
                values.append(value)
        if len(values) > 0:
            return sum(values)
        else:
            return 0

    def consumption_year(self) -> float:
        first_day_current_year = datetime.strptime(datetime.now().strftime("%Y") + ".01.01 00:00:00", "%Y.%m.%d %H:%M:%S")
        today = datetime.strptime(datetime.now().strftime("%Y.%m.%d") + " 00:00:00", "%Y.%m.%d %H:%M:%S")
        values = list()
        for day in range(0, today.timetuple().tm_yday-1):
            time = first_day_current_year + timedelta(days=day)
            value = self.day_series.get(time.strftime("%Y.%m.%d"), None)
            if value is not None:
                values.append(value)
        values.append(self.consumption_day())
        return sum(values)

    def estimated_consumption_365_days(self) -> float:
        today = datetime.strptime(datetime.now().strftime("%Y.%m.%d") + " 00:00:00", "%Y.%m.%d %H:%M:%S")
        one_year_ago = today - timedelta(days=365)
        values = list()
        for day in range(0, 365):  # ignore today
            time = one_year_ago + timedelta(days=day)
            value = self.day_series.get(time.strftime("%Y.%m.%d"), None)
            if value is not None:
                values.append(value)
        if len(values) > 1:
            values = values[1:]   # remove the oldest entry (typically, not a whole day)
            estimated = (sum(values) * 365) / len(values)
            return estimated
        else:
            return 0



class ConsumptionCounterRecorder(ConsumptionRecorder):

    def __init__(self, name: str):
        self.hour_resolution = SimpleDB(name + "_hour_resolution", sync_period_sec=60)
        super().__init__(name)

    def clear(self):
        self.hour_resolution.clear()

    def record(self, counter_value: float):
        now = datetime.now()
        self.hour_resolution.put(now.strftime("%Y.%m.%d %H"), counter_value, ttl_sec=3 * 365 * 24 * 60 * 60)  # ttl: 3 years

    def consumption_hour(self, time: datetime = None) -> float:
        if time is None:
            time = datetime.now()
        previous_counter = self.hour_resolution.get((time - timedelta(hours=1)).strftime("%Y.%m.%d %H"), 0)
        current_counter = self.hour_resolution.get(time.strftime("%Y.%m.%d %H"), 0)
        if previous_counter > 0 and current_counter > 0:
            return current_counter - previous_counter
        else:
            return 0

    def consumption_day(self, offset:int = 0) -> float:
        hour = datetime.strptime((datetime.now() + timedelta(days=offset)).strftime("%Y.%m.%d") + " 00:00:00", "%Y.%m.%d %H:%M:%S")
        consumption = 0
        while hour <= datetime.now():
            consumption += self.consumption_hour(hour)
            hour += timedelta(hours=1)
        return consumption

    def consumption_year(self) -> float:
        first_hour_current_year = datetime.strptime(datetime.now().strftime("%Y") + ".01.01 00:00:00", "%Y.%m.%d %H:%M:%S")
        keys = sorted(list(self.hour_resolution.keys()))
        if len(keys) > 2:
            for hour in keys:
                if hour >= first_hour_current_year:
                    start_count = self.hour_resolution.get(hour)
                    end_count = self.hour_resolution.get(keys[-1])
                    diff_count = end_count - start_count
                    return diff_count
        return 0

    def estimated_consumption_365_days(self) -> float:
        one_year_ago_hour = (datetime.now() - timedelta(days=365)).strftime("%Y.%m.%d %H")
        keys = sorted(list(self.hour_resolution.keys()))
        if len(keys) > 2:
            for hour in keys:
                if hour >= one_year_ago_hour:
                    start_count = self.hour_resolution.get(hour)
                    end_count = self.hour_resolution.get(keys[-1])
                    diff_count = end_count - start_count
                    start_time = datetime.strptime(hour, "%Y.%m.%d %H")
                    end_time = datetime.strptime(keys[-1], "%Y.%m.%d %H")
                    diff_seconds = (end_time - start_time).total_seconds()
                    return (365 * 24 * 60 * 60) * diff_count / diff_seconds
        return 0




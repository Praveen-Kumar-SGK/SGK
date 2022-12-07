from pymongo import MongoClient
from abc import ABCMeta, abstractmethod , abstractstaticmethod
from datetime import datetime , timedelta
import time

# singleton architecture for mongo database object
class MongoDB(object):
    __instance = None
    def __init__(self):
        self.client = MongoClient('172.28.42.150', 27017)
        if MongoDB.__instance is not None:
            raise Exception("single object cannot be instantiated more than once")
        else:
            MongoDB.__instance = self

    @staticmethod
    def get_instance():
        if MongoDB.__instance == None:
            MongoDB()
        return MongoDB.__instance

# Mongo Interface
class IMongo(metaclass=ABCMeta):
    @abstractmethod
    def translate(self):
        """implement in child class"""
        pass

    @abstractmethod
    def detect_language(self):
        pass

class MongoSearch(IMongo):

    def __init__(self,text,to_lang="en"):
        self.db_connector = MongoDB.get_instance()
        self.text = text
        self.to_lang = to_lang.lower()
        self.database_name = "ai"
        self.collection_name = "extractor_google_api"

    def translate(self):
        db_client = self.db_connector.client
        database = db_client[self.database_name]
        collection = database[self.collection_name]
        data = [document for document in collection.find({"data.mode": "translate", "data.input": self.text, "data.to_language": self.to_lang}, {"data.translatedText": 1}).limit(1)]
        if len(data) != 0:
            return data[0]["data"]["translatedText"]

    def detect_language(self):
        db_client = self.db_connector.client
        database = db_client[self.database_name]
        collection = database[self.collection_name]
        data = [document for document in collection.find({"data.mode": "language_detection", "data.input": self.text}, {"data.language": 1}).limit(1)]
        print(data)
        if len(data) != 0:
            return data[0]["data"]["language"]

class TornadoMongoSearch:
    '''this is for query mongo google api documents based on three data , start_date , end_date and wornk order numbber'''
    def __init__(self):
        self.mongo_client = MongoDB.get_instance()
        self._start_date = None
        self._end_date = None
        self._work_order = None

    @property
    def start_date(self):
        return self._start_date

    @property
    def end_date(self):
        return self._end_date

    @property
    def work_order(self):
        return self._work_order

    @start_date.setter
    def start_date(self, value):
        if value:
            self._start_date = datetime.strptime(value,"%Y-%m-%d")

    @end_date.setter
    def end_date(self, value):
        if value:
            value =  datetime.strptime(value,"%Y-%m-%d")
            if self._start_date == value:
                value += timedelta(days=1)
            self._end_date = value

    @work_order.setter
    def work_order(self, value):
        if value:
            # value = f"GS1_{value}\d*\.xml"
            value = f"GS1_{value}\d*\_?\d*\.xml"
            self._work_order = value

    def search(self):
        client = self.mongo_client.client
        print(self._start_date , self._end_date , self._work_order)
        if self._start_date and self._end_date and self._work_order:
            db = client["ai"]
            collection = db["extractor_google_api"]
            result = [{**doc["data"],**{"date":doc["date"]}} for doc in collection.find({"date": {"$gte": self._start_date, "$lt": self._end_date}, "data.mode": "translate", "data.File":{"$regex":self.work_order}})]
            return result
        elif self._start_date and self._end_date and not self._work_order:
            db = client["ai"]
            collection = db["extractor_google_api"]
            result = [{**doc["data"],**{"date":doc["date"]}} for doc in collection.find({"date": {"$gte": self._start_date, "$lt": self._end_date}, "data.mode": "translate"})]
            return result

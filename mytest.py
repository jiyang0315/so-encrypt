import datetime

class DataCenter():
    def gettime(self):
        print(datetime.datetime.now())
    def write_data(self):
        print("hello XiaoBei!")
       
if __name__=="__main__": 
    data = DataCenter()
    data.write_data()

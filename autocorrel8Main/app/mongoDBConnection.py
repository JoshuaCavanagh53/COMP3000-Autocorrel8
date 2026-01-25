from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import pymongo
from PyQt5.QtCore import pyqtSignal, QThread

uri = "mongodb+srv://JoshCav:LinuxScrub5309!@autocorrel8.jty4g7j.mongodb.net/?appName=AutoCorrel8"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


class DatabaseHelper():
    
    def __init__(self):
        
        super().__init__()
        
        # Declare database variables
        self.myclient = pymongo.MongoClient(uri)
        self.mydb = self.myclient["PacketFileDatabase"]
        self.mycol = self.mydb["PacketFiles"]


    def write_to_database(self, packets):
        # Write packets in chunks to the database
        try:
            batch_size = 5000  # safe batch size

            for i in range(0, len(packets), batch_size):
                batch = packets[i:i + batch_size]
                self.mycol.insert_many(batch)

            print(f"Inserted {len(packets)} packets into MongoDB")

        except Exception as e:
            print("Error writing packets to database:", e)

    # Grab data from the mongodb
    def fetch_from_database(self):

        try:

            x = self.mycol.find_one()

            print(x)

        except Exception as e:

            print(f"Error Fetching Data: {e}")



# Handle large database upload in the background
class DatabaseUploadThread(QThread):
    
    finished = pyqtSignal(str)   
    error = pyqtSignal(str)      

    def __init__(self, packets, file_name):
        
        super().__init__()
        self.packets = packets
        self.file_name = file_name

    def run(self):
        try:
            helper = DatabaseHelper()
            helper.write_to_database(self.packets)
            self.finished.emit(self.file_name)
        except Exception as e:
            self.error.emit(str(e))

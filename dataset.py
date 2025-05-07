from pymongo import MongoClient

# MongoDB Atlas connection
client = MongoClient("mongodb+srv://hanibenjemaa39:hani1234@cancerv3.cnjbfhn.mongodb.net/?retryWrites=true&w=majority&appName=cancerV3")
#client = MongoClient('mongodb+srv://hanibenjemaa39:hani1234@cancerv2.keq4got.mongodb.net/?retryWrites=true&w=majority&appName=cancerV2')
db = client['cancer_db']

# Collections
users_collection = db['users']
patients_collection = db['patients']
rapports_collection = db['rapports']
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import date
from bson.objectid import ObjectId
import os

class DataBaseManager:
    def __init__(self):
        mongo_password = os.environ["MONGO_PASSWORD"]
        uri = f"mongodb+srv://Bhuvansh:{mongo_password}@prodcluster.v1ojbsm.mongodb.net/?retryWrites=true&w=majority&appName=AtlasApp"
        print(uri)
        # Create a new client and connect to the server
        self.client = MongoClient(uri, server_api=ServerApi('1'))
        # Send a ping to confirm a successful connection
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)
        self.db = self.client["blogDB"]
    
    def get_all_posts(self):
        return self.db.posts.find()
    
    def get_post_by_id(self, post_id):
        return self.db.posts.find_one({"_id": ObjectId(post_id)})

    def update_post(self, post_id, new_post):
        self.db.posts.replace_one({"_id": ObjectId(post_id)}, new_post)

    def add_post(self, author_id, title, subtitle, body, img_url):
        author_name = self.db.users.find_one({"_id": ObjectId(author_id)})["name"]
        document = {
            "author_id": author_id,
            "author_name": author_name,
            "title": title,
            "subtitle": subtitle,
            "date": date.today().strftime("%B %d, %Y"),
            "body": body,
            "img_url": img_url,
            "comments": []
        }
        return self.db.posts.insert_one(document)
    
    def get_post_by_id(self, post_id):
        return self.db.posts.find_one({"_id": ObjectId(post_id)})

    def delete_post(self, post_id):
        self.db.posts.delete_one({"_id": ObjectId(post_id)})
    
    def add_user(self, user):
        document = {
            "name": user.name,
            "email": user.email,
            "password": user.password,
            "posts": []
        }
        doc_id = self.db.users.insert_one(document)
        user.set_id(doc_id.inserted_id)
    
    def get_user_by_email(self, email):
        return self.db.users.find_one({"email": email})

    def update_user(self, user_id, new_user):
        document = {
            "name": new_user.name,
            "email": new_user.email,
            "password": new_user.password,
            "posts": new_user.posts
        }
        self.db.users.replace_one({"_id": ObjectId(user_id)}, document)

    def get_user_by_id(self, user_id):
        return self.db.users.find_one({"_id": ObjectId(user_id)})
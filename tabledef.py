from sqlalchemy import *
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Date, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
import random
import string
import hashlib

engine = create_engine('sqlite:///users.db', echo=True)
Base = declarative_base()
 
class User(Base):
    __tablename__ = "users"
 
    id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(String)
    salt = Column(String)
 
    def __init__(self, username, password):
        self.username = username
        self.salt = self.gen_rand_salt()
        print 'Salt:', self.salt
        self.password = hashlib.sha512(password + self.salt).hexdigest()

    def gen_rand_salt(self):
        ret = ''
        for i in range(10):
            ret += random.choice(string.ascii_letters)
        return ret
 
# create tables
Base.metadata.create_all(engine)
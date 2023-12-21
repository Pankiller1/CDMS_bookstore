
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    user_id = Column(String(200), primary_key=True)
    password = Column(String(200), nullable=False)
    balance = Column(Integer, nullable=False)
    token = Column(String(2000))
    terminal = Column(String(200))


class UserStore(Base):
    __tablename__ = 'user_store'

    user_id = Column(String(200), ForeignKey('user.user_id'), primary_key=True)
    store_id = Column(String(200), primary_key=True)


class Store(Base):
    __tablename__ = 'store'

    store_id = Column(String(200), primary_key=True)
    book_id = Column(String(200), primary_key=True)
    book_title = Column(String(200))
    book_author = Column(String(200))
    book_price = Column(Integer)
    stock_level = Column(Integer)


class NewOrder(Base):
    __tablename__ = 'new_order'

    order_id = Column(String(200), primary_key=True)
    user_id = Column(String(200))
    store_id = Column(String(200))
    payment_ddl = Column(Integer)
    payment_status = Column(String(50))


class NewOrderDetail(Base):
    __tablename__ = 'new_order_detail'

    order_id = Column(String(200), ForeignKey('new_order.order_id'), primary_key=True)
    book_id = Column(String(200), primary_key=True)
    count = Column(Integer)
    price = Column(Integer)


class MySQLStore:
    def __init__(self, db_url):
        self.engine = create_engine(db_url, echo=True)  # Set echo to True for debugging
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_session(self):
        return self.session


database_instance: MySQLStore = None


def init_database(db_url):
    global database_instance
    database_instance = MySQLStore(db_url)


def get_db_conn():
    global database_instance
    return database_instance.get_session()


db_url = "mysql+pymysql://root:123456@localhost:3306/bookstore?charset=utf8"
init_database(db_url)
session = get_db_conn()

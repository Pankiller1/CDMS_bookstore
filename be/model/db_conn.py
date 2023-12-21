from be.model import store
from be.model.store import User, Store, UserStore
from sqlalchemy.orm import sessionmaker


class DBConn:
    def __init__(self):
        self.session = store.get_db_conn()

    def user_id_exist(self, user_id):
        result = self.session.query(User).filter(User.user_id == user_id).first()
        return result is not None

    def book_id_exist(self, store_id, book_id):
        result = (
            self.session.query(Store)
            .filter(Store.store_id == store_id, Store.book_id == book_id)
            .first()
        )
        return result is not None

    def store_id_exist(self, store_id):
        result = self.session.query(UserStore).filter(UserStore.store_id == store_id).first()
        return result is not None

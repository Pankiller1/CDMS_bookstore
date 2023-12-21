from be.model import error
from be.model import db_conn
from be.model import store
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import time


class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(
            self,
            user_id: str,
            store_id: str,
            book_id: str,
            book_title: str,
            book_author: str,
            book_price: int,
            stock_level: int,
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            new_book = store.Store(store_id=store_id, book_id=book_id, book_title=book_title, book_author=book_author,
                                   book_price=book_price, stock_level=stock_level)
            self.session.add(new_book)
            self.session.commit()

        except IntegrityError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def add_stock_level(
            self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            result = self.session.query(store.Store).filter_by(store_id=store_id, book_id=book_id).update({
                store.Store.stock_level: store.Store.stock_level + add_stock_level
            })

            if result is None:
                return error.error_non_exist_book_id(book_id)
            self.session.commit()

        except IntegrityError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            new_store = store.UserStore(user_id=user_id, store_id=store_id)
            self.session.add(new_store)
            self.session.commit()

        except IntegrityError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def search_order(self, user_id) -> (int, str):
        try:
            # 搜索前遍历订单删除超时订单
            current_time = int(time.time())
            payment_overtime_order_ids = self.session.query(store.NewOrder).filter(
                store.NewOrder.payment_ddl < current_time, store.NewOrder.payment_status == "no_pay").all()
            for row in payment_overtime_order_ids:
                order_id = row.order_id
                self.session.query(store.NewOrderDetail).filter_by(order_id=order_id).delete()
                self.session.query(store.NewOrder).filter_by(order_id=order_id).delete()

            # 将用户作为卖家进行搜索
            # 获取卖家名下店铺
            seller_store_ids = self.session.query(store.UserStore).filter_by(user_id=user_id).all()
            for row in seller_store_ids:
                store_id = row.store_id
                seller_order_ids = self.session.query(store.NewOrder).filter_by(store_id=store_id).all()

                if seller_order_ids.__len__() == 0:
                    return error.empty_order_search(user_id)

                for detail in seller_order_ids:
                    order_id = detail.order_id
                    self.session.query(store.NewOrder).filter_by(order_id=order_id).all()

            # seller_store_ids = [store['store_id'] for store in
            #                     self.conn.user_store_col.find({"user_id": user_id}, {"store_id": 1})]
            # 通过店铺store_id搜索订单order_id
            # seller_order_ids = [order['order_id'] for order in
            #                     self.conn.new_order_col.find({"store_id": {"$in": seller_store_ids}},
            #                                                  {"order_id": 1})]
            # if not seller_order_ids:
            #     return error.empty_order_search(user_id)
            # self.conn.new_order_col.find({"order_id": {"$in": seller_order_ids}}, {})
            self.session.commit()
        except IntegrityError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def deliver(self, user_id: str, store_id: str, order_id: str) -> (int, str):
        try:
            result = self.session.query(store.NewOrder).filter_by(order_id=order_id).first()
            if result is None:
                return error.error_non_exist_order(order_id)

            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)

            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)

            status = result.payment_status

            if status == "no_pay":
                return error.error_order_no_pay(order_id)
            elif status == "shipped" or status == "received":
                return error.error_order_already_received(order_id)

            self.session.query(store.NewOrder).filter_by(order_id=order_id).update({
                store.NewOrder.payment_status: "shipped"
            })
            self.session.commit()
        except IntegrityError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"


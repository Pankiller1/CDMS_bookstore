import uuid
import logging
from be.model import db_conn
from be.model import error
from be.model import store
from sqlalchemy.orm import sessionmaker
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
import time


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
            self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            current_time = int(time.time())
            payment_ddl = current_time + 15
            new_order = store.NewOrder(order_id=uid, user_id=user_id, store_id=store_id, payment_status="no_pay",
                                       payment_ddl=payment_ddl)
            self.session.add(new_order)

            for book_id, count in id_and_count:
                result = self.session.query(store.Store).filter_by(store_id=store_id, book_id=book_id).first()
                if result is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = result.stock_level
                price = result.book_price

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                result = self.session.query(store.Store).filter_by(store_id=store_id, book_id=book_id).update({
                    store.Store.stock_level: store.Store.stock_level - count
                })

                if result is None:
                    return error.error_stock_level_low(book_id) + (order_id,)

                new_order_detail = store.NewOrderDetail(order_id=uid, book_id=book_id, count=count, price=price)
                self.session.add(new_order_detail)

            self.session.commit()

            order_id = uid
        except IntegrityError as e:
            logging.info("528, {}".format(str(e)))
            print(f"IntegrityError: {e}")
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            result = self.session.query(store.NewOrder).filter_by(order_id=order_id).first()
            if result is None:
                return error.error_invalid_order_id(order_id)
            if result.payment_status != "no_pay":
                return

            order_id = result.order_id
            buyer_id = result.user_id
            store_id = result.store_id

            if buyer_id != user_id:
                return error.error_authorization_fail()

            result = self.session.query(store.User).filter_by(user_id=buyer_id).first()
            if result is None:
                return error.error_non_exist_user_id(buyer_id)

            balance = result.balance
            if password != result.password:
                return error.error_authorization_fail()

            result = self.session.query(store.UserStore).filter_by(store_id=store_id).first()
            if result is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = result.user_id

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            result = self.session.query(store.NewOrderDetail).filter_by(order_id=order_id).all()

            total_price = 0
            for row in result:
                count = row.count
                price = row.price
                total_price = total_price + price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            result = self.session.query(store.User).filter_by(user_id=buyer_id).update({
                store.User.balance: store.User.balance - total_price
            })
            if result == 0:
                return error.error_not_sufficient_funds(order_id)

            result = self.session.query(store.User).filter_by(user_id=seller_id).update({
                store.User.balance: store.User.balance + total_price
            })

            if result is None:
                return error.error_non_exist_user_id(seller_id)

            result = self.session.query(store.NewOrder).filter_by(order_id=order_id).update({
                store.NewOrder.payment_status: "paid"
            })
            if result is None:
                return error.error_invalid_order_id(order_id)
            self.session.commit()

        except IntegrityError as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            result = self.session.query(store.User).filter_by(user_id=user_id).first()
            if result is None:
                return error.error_authorization_fail()

            if result.password != password:
                return error.error_authorization_fail()

            result = self.session.query(store.User).filter_by(user_id=user_id).update({
                store.User.balance: store.User.balance + add_value
            })
            if result is None:
                return error.error_non_exist_user_id(user_id)

            self.session.commit()
        except IntegrityError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def book_search(self, store_id, book_id, book_title, book_author):
        try:
            query_conditions = {}
            if store_id:
                query_conditions["store_id"] = store_id
            if book_id:
                query_conditions["book_id"] = book_id
            if book_title:
                query_conditions["book_title"] = book_title
            if book_author:
                query_conditions["book_author"] = book_author

            result = self.session.query(store.Store).filter_by(**query_conditions).all()
            if not result:
                return error.error_non_exist_book_id(book_id)

            self.session.commit()
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    # 删除订单操作
    def delete_order(self, user_id, order_id) -> (int, str):
        try:
            # 获取订单信息
            result = self.session.query(store.NewOrder).filter_by(order_id=order_id).first()
            # 判断有无订单删除
            if result is None:
                return error.error_non_order_delete(user_id)
            payment_status = result.payment_status
            # 如果有订单
            if payment_status == "paid":
                # 按照order_id查找store_id并存储
                result = self.session.query(store.NewOrder).filter_by(order_id=order_id).first()

                if result is None:
                    return error.error_invalid_order_id(order_id)
                store_id = result.store_id

                if store_id is None:
                    return error.error_non_exist_store_id(store_id)

                # 通过store_id查找卖家
                seller_id = self.session.query(store.UserStore).filter_by(store_id=store_id).first()

                if seller_id is None:
                    return error.error_non_exist_user_id(seller_id)
                # 如果支付状态是"paid"
                # 通过order_id查找购买书籍并计算价格总和
                result = self.session.query(store.NewOrderDetail).filter_by(order_id=order_id).all()

                total_price = 0
                for row in result:
                    count = row.count
                    price = row.price
                    total_price = total_price + price * count

                # 用户余额返回
                result = self.session.query(store.User).filter_by(user_id=user_id).update({
                    store.User.balance: store.User.balance + total_price
                })
                if result is None:
                    return error.error_non_exist_user_id(user_id)

                # 卖家用户减少余额
                result = self.session.query(store.User).filter_by(user_id=seller_id).update({
                    store.User.balance: store.User.balance - total_price
                })
                if result is None:
                    return error.error_non_exist_user_id(seller_id)

                # 删除状态为"no_pay"与"paid"的订单
                self.session.query(store.NewOrderDetail).filter_by(order_id=order_id).delete()
                self.session.query(store.NewOrder).filter_by(order_id=order_id).delete()

            elif payment_status == "no_pay":
                # 还未付款直接删除,无需退钱
                # 删除状态为"no_pay"与"paid"的订单
                self.session.query(store.NewOrderDetail).filter_by(order_id=order_id).delete()
                self.session.query(store.NewOrder).filter_by(order_id=order_id).delete()

            else:
                return error.error_unable_to_delete(order_id)
            self.session.commit()
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def search_order(self, user_id) -> (int, str):
        try:
            # 搜索前遍历订单删除超时订单
            current_time = int(time.time())
            result = self.session.query(store.NewOrder).filter(
                store.NewOrder.payment_ddl < current_time, store.NewOrder.payment_status == "no_pay").all()

            for row in result:
                order_id = row.order_id
                self.session.query(store.NewOrderDetail).filter_by(order_id=order_id).delete()
                self.session.query(store.NewOrder).filter_by(order_id=order_id).delete()

            # 将用户作为买家进行搜索
            result = self.session.query(store.NewOrder).filter_by(user_id=user_id).all()
            if result.__len__() == 0:
                return error.empty_order_search(user_id)

            for row in result:
                order_id = row.order_id
                self.session.query(store.NewOrder).filter_by(order_id=order_id).first()
            self.session.commit()
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def receive(self, user_id: str, store_id: str, order_id: str) -> (int, str):
        try:
            result = self.session.query(store.NewOrder).filter_by(order_id=order_id).first()
            if result is None:
                return 503, "no order exists"

            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)

            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)

            status = result.payment_status

            if status == "no_pay":
                return error.error_order_no_pay(order_id)
            elif status == "paid":
                return error.error_order_no_shipped(order_id)
            elif status == "received":
                return error.error_order_already_received(order_id)

            self.session.query(store.NewOrder).filter_by(order_id=order_id).update({
                store.NewOrder.payment_status: "received"
            })
            self.session.commit()

        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

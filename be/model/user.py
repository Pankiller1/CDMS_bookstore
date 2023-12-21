import jwt
import time
import logging
from be.model import error
from be.model import db_conn
from be.model import store
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError


# encode a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }


def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded.encode("utf-8").decode("utf-8")


# decode a JWT to a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }
def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class User(db_conn.DBConn):
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        db_conn.DBConn.__init__(self)

    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False

    def register(self, user_id: str, password: str):
        try:
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            new_user = store.User(user_id=user_id, password=password, balance=0, token=token, terminal=terminal)
            self.session.add(new_user)
            self.session.commit()

        except IntegrityError as e:
            self.session.rollback()
            return error.error_exist_user_id(user_id)
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        # print("begin check")
        result = self.session.query(store.User.token).filter_by(user_id=user_id).first()
        if result is None:
            return error.error_authorization_fail()
        # print("result is not none")
        if not self.__check_token(user_id, result[0], token):
            # print(result[0])
            # print(token)
            return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        result = self.session.query(store.User.password).filter_by(user_id=user_id).first()
        if result is None:
            return error.error_authorization_fail()
        if password != result[0]:
            return error.error_authorization_fail()
        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        token = ""
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = jwt_encode(user_id, terminal)
            result = self.session.query(store.User).filter_by(user_id=user_id).update({
                store.User.token: token,
                store.User.terminal: terminal
            })

            if result == 0:
                return error.error_authorization_fail() + ("",)

            self.session.commit()

        except BaseException as e:
            return 530, "{}".format(str(e)), ""
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            print(terminal)
            dummy_token = jwt_encode(user_id, terminal)

            result = self.session.query(store.User).filter_by(user_id=user_id).update({
                store.User.token: dummy_token,
                store.User.terminal: terminal
            })
            if result == 0:
                return error.error_authorization_fail()

            self.session.commit()
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message
            result = self.session.query(store.User).filter_by(user_id=user_id).delete()
            if result == 1:
                self.session.commit()
            else:
                return error.error_authorization_fail()
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def change_password(
            self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)

            result = self.session.query(store.User).filter_by(user_id=user_id).update({
                store.User.password: new_password,
                store.User.token: token,
                store.User.terminal: terminal
            })

            if result == 0:
                return error.error_authorization_fail()

            self.session.commit()

        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

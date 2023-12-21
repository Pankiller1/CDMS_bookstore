from flask import Blueprint
from flask import request
from flask import jsonify
from be.model import seller
import json

bp_seller = Blueprint("seller", __name__, url_prefix="/seller")


@bp_seller.route("/create_store", methods=["POST"])
def seller_create_store():
    user_id: str = request.json.get("user_id")
    store_id: str = request.json.get("store_id")
    s = seller.Seller()
    code, message = s.create_store(user_id, store_id)
    return jsonify({"message": message}), code


@bp_seller.route("/add_book", methods=["POST"])
def seller_add_book():
    user_id: str = request.json.get("user_id")
    store_id: str = request.json.get("store_id")
    book_info = request.json.get("book_info")
    stock_level: int = request.json.get("stock_level", 0)

    s = seller.Seller()
    code, message = s.add_book(
        user_id, store_id, book_info.get("id"), book_info.get("title"), book_info.get("author"), book_info.get("price"),
        stock_level
    )

    return jsonify({"message": message}), code


@bp_seller.route("/add_stock_level", methods=["POST"])
def add_stock_level():
    user_id: str = request.json.get("user_id")
    store_id: str = request.json.get("store_id")
    book_id: str = request.json.get("book_id")
    add_num: int = request.json.get("add_stock_level", 0)

    s = seller.Seller()
    code, message = s.add_stock_level(user_id, store_id, book_id, add_num)

    return jsonify({"message": message}), code


# 接收搜索订单请求
@bp_seller.route("/search_order", methods=["POST"])
def search_order():
    # 请求需传入user_id
    user_id: str = request.json.get("user_id")
    s = seller.Seller()
    code, message = s.search_order(user_id)
    return jsonify({"message": message}), code


@bp_seller.route("/deliver", methods=["POST"])
def deliver():
    user_id: str = request.json.get("user_id")
    order_id: str = request.json.get("order_id")
    store_id: str = request.json.get("store_id")
    s = seller.Seller()
    code, message = s.deliver(user_id, store_id, order_id)
    return jsonify({"message": message}), code
import datetime
from enum import Enum
import os
import pathlib
import random
import re
from datetime import date, datetime, timedelta

import pymongo
from bson import ObjectId
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import db
from enums import TransactionStatus

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = APP_ROOT + "/static"

app = Flask(__name__)
app.secret_key = "pkmnbgthyjukiledcxsw"


# landing page
@app.route("/")
@app.route("/index")
def index():
    session.clear()
    # calculate delayed days and late fees
    today = datetime.today()
    transactions = db.transactions.find({"status": TransactionStatus.CHECKED_IN.value})
    for item in transactions:
        trans_id = item["_id"]
        due_date = item["due_date"]
        delayed_days = (today - due_date).days
        late_fee = float(delayed_days)
        values = ""
        if delayed_days > 0:
            values = {
                "is_delayed": True,
                "delayed_days": int(delayed_days),
                "late_fee": late_fee,
                "show_remainder": True,
            }
        if delayed_days > -3 and delayed_days < 0:
            values = {
                "show_remainder": True,
            }
        if values:
            db.transactions.update_one({"_id": ObjectId(trans_id)}, {"$set": values})

    return render_template("/index.html")


# admin Views
@app.route("/admin/", methods=["GET", "POST"])
@app.route("/admin/login/", methods=["GET", "POST"])
def admin_login():
    session.clear()
    error_msg = ""
    if request.method == "POST":
        values = {
            "username": request.form.get("username"),
            "password": request.form.get("password"),
        }

        result = db.admins.find_one(values)
        if result:
            session["logged_in"] = True
            del result["password"]
            session["fullname"] = result["fullname"]
            session["role"] = result["role"]
            return redirect(url_for("admin_home"))
        else:
            error_msg = "Invalid Login Credentials"

    admin = db.admins.find_one({})
    if not admin:
        values = {
            "username": "admin",
            "password": "admin",
            "fullname": "Administrator",
            "role": "Admin",
        }
        db.admins.insert_one(values)

    return render_template("/admin_login.html", error_msg=error_msg)


@app.route("/admin/home/")
def admin_home():
    dashboard = {
        "batches": 0,
        "started_projects": 0,
        "completed_projects": 0,
    }
    return render_template("/admin/home.html", dashboard=dashboard)


@app.route("/admin/locations/", methods=["GET", "POST"])
def admin_locations():
    location = ""
    if request.method == "POST":
        id = request.form.get("location_id")
        name = request.form.get("name").title()
        if not id:
            # Add Location
            db.locations.insert_one({"name": name, "status": True})
            flash("Location added successfully", "success")
            return redirect(url_for("admin_locations"))
        else:
            # Update Location
            result = db.locations.update_one(
                {"_id": ObjectId(id)}, {"$set": {"name": name}}
            )
            if result.modified_count > 0:
                flash("Location updated successfully", "success")
            else:
                flash("No changes made", "warning")

            return redirect(url_for("admin_locations"))

    if request.args.get("id"):
        location = db.locations.find_one({"_id": ObjectId(request.args.get("id"))})

    locations = db.locations.find({"status": True}).sort("_id", -1)
    if not locations:
        return abort(404, "Sorry, Location not found")

    return render_template(
        "/admin/locations.html", locations=locations, location=location
    )


# delete locations
@app.route("/admin/locations/delete")
def admin_locationt_delete():
    location_id = request.args.get("id")
    location = db.locations.find_one({"_id": ObjectId(location_id)})
    if not location:
        return abort(404, "Locations not found")
    db.locations.update_one({"_id": ObjectId(location_id)}, {"$set": {"status": False}})
    flash("Location deleted successfully", "success")
    return redirect(url_for("admin_locations"))


# admin view books
@app.route("/admin/books/")
def admin_books():
    books = db.books.find({"status": True})
    books = list(books)
    list.reverse(books)
    return render_template("/admin/books.html", books=books)


# admin add book
@app.route("/admin/book/add", methods=["GET", "POST"])
def admin_book_add():
    if request.method == "POST":
        id = ObjectId()
        image = request.files.get("image")
        ext = pathlib.Path(image.filename).suffix
        img_file_name = str(id) + ext
        values = {
            "_id": id,
            "isbn": request.form.get("isbn"),
            "name": request.form.get("name"),
            "author": request.form.get("author"),
            "publisher": request.form.get("publisher"),
            "year": request.form.get("year"),
            "language": request.form.get("language"),
            "description": request.form.get("description"),
            "img_file_name": img_file_name,
            "status": True,
        }
        db.books.insert_one(values)
        image.save(APP_ROOT + "/uploads/books/" + img_file_name)
        flash("Book added successfully", "success")
        return redirect(url_for("admin_books"))

    book = ""
    return render_template(
        "/admin/book_form.html",
        book=book,
    )


# admin faculty edit
@app.route("/admin/book/edit", methods=["GET", "POST"])
def admin_book_edit():
    if request.method == "POST":
        book_id = request.form.get("book_id")
        image = request.files.get("image")
        img_file_name = request.form.get("img_file_name")

        if image.filename != "":
            ext = pathlib.Path(image.filename).suffix
            img_file_name = str(book_id) + ext

        values = {
            "isbn": request.form.get("isbn"),
            "name": request.form.get("name"),
            "author": request.form.get("author"),
            "language": request.form.get("language"),
            "description": request.form.get("description"),
            "img_file_name": img_file_name,
        }
        result = db.books.update_one({"_id": ObjectId(book_id)}, {"$set": values})
        if result.modified_count > 0:
            # Save recipe image if uploaded
            if image.filename != "":
                image.save(APP_ROOT + "/uploads/books/" + image.filename)
            flash("Book updated successfully", "success")
        return redirect(url_for("admin_books"))

    book_id = request.args.get("id")
    book = db.books.find_one({"_id": ObjectId(book_id)})
    if not book:
        return abort(404, "Book not found")

    return render_template("/admin/book_form.html", book=book)


# admin delete book
@app.route("/admin/book/delete", methods=["GET", "POST"])
def admin_book_delete():
    book_id = request.args.get("id")
    book = db.books.find_one({"_id": ObjectId(book_id)})
    if not book:
        return abort(404, "Book not found")

    db.books.update_one({"_id": ObjectId(book_id)}, {"$set": {"status": False}})
    flash("Book removed successfully", "success")
    return redirect(url_for("admin_books"))


# admin view book
@app.route("/admin/book/view", methods=["GET", "POST"])
def admin_book_view():
    book_id = request.args.get("id")
    book = db.books.find_one({"_id": ObjectId(book_id), "status": True})
    if not book:
        return abort(404, "Book not found")
    return render_template("/admin/book_details.html", book=book)


# admin view stocks
@app.route("/admin/stocks")
def admin_stocks():
    stocks = db.stores.aggregate(
        [
            {
                "$lookup": {
                    "from": db.books.name,
                    "localField": "book_id",
                    "foreignField": "_id",
                    "as": "book",
                }
            },
            {"$unwind": "$book"},
            {
                "$lookup": {
                    "from": db.locations.name,
                    "localField": "location_id",
                    "foreignField": "_id",
                    "as": "location",
                }
            },
            {"$unwind": "$location"},
            {
                "$group": {
                    "_id": "$book_id",
                    "book": {"$first": "$book"},
                    "locations": {"$push": "$location"},
                    "quantity": {"$push": "$quantity"},
                }
            },
        ]
    )
    stocks = list(stocks)
    return render_template("/admin/stock.html", stocks=stocks)


# admin update stock
@app.route("/admin/stock/update", methods=["GET", "POST"])
def admin_stock_update():
    if request.method == "POST":
        book_id = request.form.get("book_id")
        location_id = request.form.get("location_id")
        quantity = request.form.get("quantity")

        values = {
            "book_id": ObjectId(book_id),
            "location_id": ObjectId(location_id),
            "quantity": int(quantity),
        }

        stock = db.stores.update_one(
            {"book_id": ObjectId(book_id), "location_id": ObjectId(location_id)},
            {"$set": values},
            upsert=True,
        )
        flash("Stock updated successfully", "success")
        return redirect(url_for("admin_stocks"))

    books = db.books.find({"status": True})
    locations = db.locations.find({"status": True})
    return render_template(
        "/admin/stock_update_form.html", locations=locations, books=books
    )


# admin view members
@app.route("/admin/members")
def admin_view_members():
    members = db.members.find({})#.sort({"status": -1, "_id": -1})
    return render_template("/admin/members.html", members=members)


# admin view member details
@app.route("/admin/member/details")
def admin_view_member_details():
    member_id = request.args.get("id")
    member = db.members.find_one({"_id": ObjectId(member_id)})

    total_books_taken = db.transactions.count_documents(
        {"member_id": ObjectId(member_id)}
    )
    checkedout_books = db.transactions.count_documents(
        {
            "member_id": ObjectId(member_id),
            "status": TransactionStatus.CHECKED_OUT.value,
        }
    )
    books_in_hand = total_books_taken - checkedout_books

    book_details = {
        "total_books_taken": total_books_taken,
        "checkedout_books": checkedout_books,
        "books_in_hand": books_in_hand,
    }

    return render_template(
        "/admin/member_details.html", member=member, book_details=book_details
    )


# admin delete member
@app.route("/admin/member/delete")
def admin_delete_member():
    member_id = request.args.get("id")
    member = db.members.find_one({"_id": ObjectId(member_id), "status": True})
    if not member:
        return abort(404, "Sorry, Member not found")
    db.members.update_one({"_id": ObjectId(member_id)}, {"$set": {"status": False}})
    flash("Member deleted successfully", "success")
    return redirect(url_for("admin_view_members"))


# admin view transactions
@app.route("/admin/transactions")
def admin_view_transactions():
    transactions = db.transactions.aggregate(
        [
            {
                "$lookup": {
                    "from": db.books.name,
                    "localField": "book_id",
                    "foreignField": "_id",
                    "as": "book",
                }
            },
            {"$unwind": "$book"},
            {
                "$lookup": {
                    "from": db.members.name,
                    "localField": "member_id",
                    "foreignField": "_id",
                    "as": "member",
                }
            },
            {"$unwind": "$member"},
            {"$sort": {"status": 1, "_id": -1}},
        ]
    )

    transactions = list(transactions)

    return render_template(
        "/admin/transactions.html",
        transactions=transactions,
        TransactionStatus=TransactionStatus,
    )


# admin view transaction details
@app.route("/admin/transaction/details")
def admin_transaction_details():
    transaction_id = request.args.get("id")
    transaction = db.transactions.aggregate(
        [
            {"$match": {"_id": ObjectId(transaction_id)}},
            {
                "$lookup": {
                    "from": db.books.name,
                    "localField": "book_id",
                    "foreignField": "_id",
                    "as": "book",
                }
            },
            {"$unwind": "$book"},
            {
                "$lookup": {
                    "from": db.members.name,
                    "localField": "member_id",
                    "foreignField": "_id",
                    "as": "member",
                }
            },
            {"$unwind": "$member"},
            {
                "$lookup": {
                    "from": db.locations.name,
                    "localField": "checkin_location_id",
                    "foreignField": "_id",
                    "as": "in_location",
                }
            },
            {"$unwind": "$in_location"},
            {
                "$lookup": {
                    "from": db.locations.name,
                    "localField": "checkout_location_id",
                    "foreignField": "_id",
                    "as": "out_location",
                }
            },
            {"$unwind": {"path": "$out_location", "preserveNullAndEmptyArrays": True}},
        ]
    )
    transaction = list(transaction)
    return render_template(
        "/admin/transaction_details.html",
        transaction=transaction[0],
        TransactionStatus=TransactionStatus,
    )


# Member registration
@app.route("/member/registration", methods=["GET", "POST"])
def member_registration():
    if request.method == "POST":
        values = {
            "firstname": request.form.get("firstname"),
            "lastname": request.form.get("lastname"),
            "email": request.form.get("email"),
            "address": request.form.get("address"),
            "mobile": request.form.get("mobile"),
            "password": request.form.get("confirmpassword"),
            "role": "Member",
            "registered_on": str(date.today()),
            "status": True,
        }
        db.members.insert_one(values)
        flash("Registerd Successfully, Please login", "success")
        return redirect(url_for("member_login"))

    return render_template("/member_registration.html")


# Member login
@app.route("/member/login", methods=["GET", "POST"])
def member_login():
    error_msg = ""
    if request.method == "POST":
        values = {
            "email": request.form.get("email"),
            "password": request.form.get("password"),
            "status": True,
        }

        result = db.members.find_one(values)
        if result:
            session["logged_in"] = True
            session["member_id"] = str(result["_id"])
            del result["password"]
            session["firstname"] = result["firstname"]
            session["role"] = result["role"]
            return redirect(url_for("member_home"))
        else:
            error_msg = "Invalid Login Credentials"

    return render_template("/member_login.html", error_msg=error_msg)


# faculty home
@app.route("/member/home")
def member_home():
    member_id = session["member_id"]
    total_books_taken = db.transactions.count_documents(
        {"member_id": ObjectId(member_id)}
    )
    checkedout_books = db.transactions.count_documents(
        {
            "member_id": ObjectId(member_id),
            "status": TransactionStatus.CHECKED_OUT.value,
        }
    )
    books_in_hand = total_books_taken - checkedout_books

    dashboard = {
        "total_books_taken": total_books_taken,
        "checkedout_books": checkedout_books,
        "books_in_hand": books_in_hand,
    }

    transactions = db.transactions.aggregate(
        [
            {
                "$match": {
                    "member_id": ObjectId(session["member_id"]),
                    "status": TransactionStatus.CHECKED_IN.value,
                    "show_remainder": True,
                }
            },
            {
                "$lookup": {
                    "from": db.books.name,
                    "localField": "book_id",
                    "foreignField": "_id",
                    "as": "book",
                }
            },
            {"$unwind": "$book"},
            {"$sort": {"status": 1, "_id": -1}},
        ]
    )

    transactions = list(transactions)
    return render_template(
        "/member/home.html",
        dashboard=dashboard,
        transactions=transactions,
        TransactionStatus=TransactionStatus,
    )


# member profile
@app.route("/member/profile", methods=["GET", "POST"])
def member_profile():
    if request.method == "POST":
        member_id = request.form.get("member_id")
        fullname = request.form.get("fullname")
        values = {
            "fullname": fullname,
            "email": request.form.get("email"),
            "mobile": request.form.get("mobile"),
        }
        result = db.members.update_one({"_id": ObjectId(member_id)}, {"$set": values})
        if result.modified_count > 0:
            session["fullname"] = fullname
            flash("Profile updated successfully", "success")

        return redirect(url_for("member_profile"))

    member = db.members.find_one({"_id": ObjectId(session["member_id"])})
    return render_template(
        "/member/profile.html",
        member=member,
    )


# member change password
@app.route("/member/change-password", methods=["GET", "POST"])
def member_change_password():
    member_id = session["member_id"]
    if request.method == "POST":
        values = {
            "password": request.form.get("password"),
        }
        db.members.update_one({"_id": ObjectId(member_id)}, {"$set": values})
        flash("Password Updated successfully", "success")
        return redirect(url_for("member_change_password"))

    return render_template("/member/change_password.html")


# member view books
@app.route("/member/books")
def member_books():
    location_id = request.args.get("location_id")
    books = db.books.find({"status": True}).sort("_id", -1)
    if location_id:
        books = db.books.aggregate(
            [
                {
                    "$lookup": {
                        "from": db.stores.name,
                        "localField": "_id",
                        "foreignField": "book_id",
                        "pipeline": [
                            {
                                "$match": {
                                    "location_id": ObjectId(location_id),
                                    "quantity": {"$gt": 0},
                                }
                            }
                        ],
                        "as": "store",
                    }
                },
                {"$unwind": "$store"},
            ]
        )
        books = list(books)

    locations = db.locations.find({"status": True})
    return render_template(
        "/member/books.html", books=books, locations=locations, str=str
    )


# member view book details
@app.route("/member/book/details/")
def member_book_details():
    book_id = request.args.get("id")
    book = db.books.find_one({"_id": ObjectId(book_id), "status": True})
    stocks = db.stores.aggregate(
        [
            {"$match": {"book_id": ObjectId(book_id), "quantity": {"$gt": 0}}},
            {
                "$lookup": {
                    "from": db.locations.name,
                    "localField": "location_id",
                    "foreignField": "_id",
                    "as": "location",
                }
            },
            {"$unwind": "$location"},
        ]
    )
    stocks = list(stocks)
    is_book_taken = db.isBookTakenByMember(book["_id"], session["member_id"])
    transaction = db.transactions.find_one(
        {
            "book_id": ObjectId(book_id),
            "member_id": ObjectId(session["member_id"]),
            "status": TransactionStatus.CHECKED_IN.value,
        }
    )

    book_available_date = db.getBookAvailableDate(book_id)
    if book_available_date:
        book_available_date = book_available_date + timedelta(days=1)

    reserved = db.reserved_books.find_one(
        {"book_id": ObjectId(book_id), "member_id": ObjectId(session["member_id"])}
    )

    return render_template(
        "/member/book_details.html",
        book=book,
        stocks=stocks,
        is_book_taken=is_book_taken,
        transaction=transaction,
        book_available_date=book_available_date,
        reserved=reserved,
    )


# Member check-in-book
@app.route("/member/check-in-book/", methods=["GET", "POST"])
def member_check_in_book():
    if request.method == "POST":
        book_id = request.form.get("book_id")
        location_id = request.form.get("location_id")
        check_in_date = datetime.today()
        due_date = check_in_date + timedelta(days=14)
        values = {
            "book_id": ObjectId(book_id),
            "checkin_location_id": ObjectId(location_id),
            "member_id": ObjectId(session["member_id"]),
            "check_in_date": check_in_date,
            "due_date": due_date,
            "check_out_date": "",
            "checkout_location_id": "",
            "late_fee": float(0),
            "delayed_days": int(0),
            "is_delayed": False,
            "is_paid": False,
            "is_extended": False,
            "status": TransactionStatus.CHECKED_IN.value,
        }
        db.transactions.insert_one(values)
        # update stock
        store = db.stores.find_one(
            {"book_id": ObjectId(book_id), "location_id": ObjectId(location_id)}
        )
        if store:
            old_qty = int(store["quantity"])
            updated_qty = old_qty - 1
            db.stores.update_one(
                {"_id": ObjectId(store["_id"])}, {"$set": {"quantity": updated_qty}}
            )

            db.reserved_books.delete_one(
                {
                    "book_id": ObjectId(book_id),
                    "member_id": ObjectId(session["member_id"]),
                }
            )
            flash("Book Checked-Out successfully", "success")
            return redirect(url_for("member_view_transactions"))

    book_id = request.args.get("id")
    book = db.books.find_one({"_id": ObjectId(book_id), "status": True})
    if not book:
        return abort(404, "Sorry, Book not Found")

    location_list = db.stores.aggregate(
        [
            {"$match": {"book_id": ObjectId(book_id), "quantity": {"$gt": 0}}},
            {
                "$lookup": {
                    "from": db.locations.name,
                    "localField": "location_id",
                    "foreignField": "_id",
                    "as": "location",
                }
            },
            {"$unwind": "$location"},
            {"$group": {"_id": "$location_id", "locations": {"$push": "$location"}}},
        ]
    )

    location_list = list(location_list)

    return render_template(
        "/member/check_in_form.html", book=book, location_list=location_list
    )


# member checkout book
@app.route("/member/check-out-book/", methods=["GET", "POST"])
def member_check_out_book():
    if request.method == "POST":
        # update transaction collection
        transaction_id = request.form.get("transaction_id")
        book_id = request.form.get("book_id")
        location_id = request.form.get("location_id")

        trans_values = {
            "check_out_date": datetime.today(),
            "checkout_location_id": ObjectId(location_id),
            "status": TransactionStatus.CHECKED_OUT.value,
        }
        result = db.transactions.update_one(
            {"_id": ObjectId(transaction_id)}, {"$set": trans_values}
        )

        if result.modified_count > 0:
            # update stock
            update_quantity = int(1)
            store = db.stores.find_one(
                {"book_id": ObjectId(book_id), "location_id": ObjectId(location_id)}
            )
            if store:
                old_qty = int(store["quantity"])
                update_quantity = old_qty + update_quantity

            store_values = {
                "book_id": ObjectId(book_id),
                "location_id": ObjectId(location_id),
                "quantity": update_quantity,
            }

            stock = db.stores.update_one(
                {"book_id": ObjectId(book_id), "location_id": ObjectId(location_id)},
                {"$set": store_values},
                upsert=True,
            )

        flash("Book checked-out successfully", "success")
        return redirect(url_for("member_view_transactions"))

    transaction_id = request.args.get("id")
    transaction = db.transactions.find_one({"_id": ObjectId(transaction_id)})
    if not transaction:
        return abort(404, "Transaction not found")

    locations = db.locations.find({"status": True})
    book = db.books.find_one({"_id": ObjectId(transaction["book_id"])})

    return render_template(
        "/member/check_out_form.html",
        transaction=transaction,
        book=book,
        locations=locations,
    )


# member checkout book
@app.route("/member/pay-check-out-book/", methods=["GET", "POST"])
def member_pay_check_out_book():
    if request.method == "POST":
        # update transaction collection
        transaction_id = request.form.get("transaction_id")
        book_id = request.form.get("book_id")
        location_id = request.form.get("location_id")

        trans_values = {
            "check_out_date": datetime.today(),
            "checkout_location_id": ObjectId(location_id),
            "status": TransactionStatus.CHECKED_OUT.value,
            "is_paid": True,
        }
        result = db.transactions.update_one(
            {"_id": ObjectId(transaction_id)}, {"$set": trans_values}
        )

        if result.modified_count > 0:
            # update stock
            update_quantity = int(1)
            store = db.stores.find_one(
                {"book_id": ObjectId(book_id), "location_id": ObjectId(location_id)}
            )
            if store:
                old_qty = int(store["quantity"])
                update_quantity = old_qty + update_quantity

            store_values = {
                "book_id": ObjectId(book_id),
                "location_id": ObjectId(location_id),
                "quantity": update_quantity,
            }

            stock = db.stores.update_one(
                {"book_id": ObjectId(book_id), "location_id": ObjectId(location_id)},
                {"$set": store_values},
                upsert=True,
            )

            # update payment details
            payment_values = {
                "tranaction_id": ObjectId(transaction_id),
                "payment_date": datetime.today(),
                "late_fee_amount": float(request.form.get("late_fee")),
                "card_details": {
                    "card_name": request.form.get("card_name"),
                    "card_number": request.form.get("card_number"),
                    "exp_month": request.form.get("exp_month"),
                    "exp_year": request.form.get("exp_year"),
                    "cvv": request.form.get("cvv"),
                },
            }
            db.payments.insert_one(payment_values)

        flash("Book checked-out successfully", "success")
        return redirect(url_for("member_view_transactions"))

    transaction_id = request.args.get("id")
    transaction = db.transactions.find_one({"_id": ObjectId(transaction_id)})
    if not transaction:
        return abort(404, "Transaction not found")

    locations = db.locations.find({"status": True})
    book = db.books.find_one({"_id": ObjectId(transaction["book_id"])})
    return render_template(
        "/member/pay_check_out_form.html",
        transaction=transaction,
        book=book,
        locations=locations,
    )


# member view transactions
@app.route("/member/transactions")
def member_view_transactions():
    member_id = session["member_id"]

    transactions = db.transactions.aggregate(
        [
            {"$match": {"member_id": ObjectId(member_id)}},
            {
                "$lookup": {
                    "from": db.books.name,
                    "localField": "book_id",
                    "foreignField": "_id",
                    "as": "book",
                }
            },
            {"$unwind": "$book"},
            {"$sort": {"status": 1, "_id": -1}},
        ]
    )

    transactions = list(transactions)

    return render_template(
        "/member/transactions.html",
        transactions=transactions,
        TransactionStatus=TransactionStatus,
    )


# member view transaction details
@app.route("/member/transaction/details")
def member_transaction_details():
    transaction_id = request.args.get("id")
    transaction = db.transactions.aggregate(
        [
            {"$match": {"_id": ObjectId(transaction_id)}},
            {
                "$lookup": {
                    "from": db.books.name,
                    "localField": "book_id",
                    "foreignField": "_id",
                    "as": "book",
                }
            },
            {"$unwind": "$book"},
            {
                "$lookup": {
                    "from": db.locations.name,
                    "localField": "checkin_location_id",
                    "foreignField": "_id",
                    "as": "in_location",
                }
            },
            {"$unwind": "$in_location"},
            {
                "$lookup": {
                    "from": db.locations.name,
                    "localField": "checkout_location_id",
                    "foreignField": "_id",
                    "as": "out_location",
                }
            },
            {"$unwind": {"path": "$out_location", "preserveNullAndEmptyArrays": True}},
        ]
    )
    transaction = list(transaction)
    return render_template(
        "/member/transaction_details.html",
        transaction=transaction[0],
        TransactionStatus=TransactionStatus,
    )


# member reserve book
@app.route("/member/reserve-book/")
def member_book_reserve():
    member_id = session["member_id"]
    book_id = request.args.get("id")
    values = {
        "book_id": ObjectId(book_id),
        "member_id": ObjectId(member_id),
        "reserved_on": str(date.today()),
    }
    db.reserved_books.insert_one(values)
    flash("Book reserved successfully", "success")
    return redirect(url_for("member_book_details", id=book_id))


# member view reserved books
@app.route("/member/reserved/books")
def member_view_reserved_books():
    member_id = session["member_id"]
    reserved_books = db.reserved_books.aggregate(
        [
            {"$match": {"member_id": ObjectId(member_id)}},
            {
                "$lookup": {
                    "from": db.books.name,
                    "localField": "book_id",
                    "foreignField": "_id",
                    "as": "book",
                }
            },
            {"$unwind": "$book"},
        ]
    ) 
    reserved_books=list(reserved_books)
    return render_template("/member/reserved_books.html", reserved_books=reserved_books)


# member view checked_in books
@app.route("/member/checked-in-book")
def member_view_checked_in_books():
    member_id = session["member_id"]

    transactions = db.transactions.aggregate(
        [
            {
                "$match": {
                    "member_id": ObjectId(member_id),
                    "status": TransactionStatus.CHECKED_IN.value,
                }
            },
            {
                "$lookup": {
                    "from": db.books.name,
                    "localField": "book_id",
                    "foreignField": "_id",
                    "as": "book",
                }
            },
            {"$unwind": "$book"},
            {"$sort": {"status": 1, "_id": -1}},
        ]
    )

    transactions = list(transactions)

    return render_template(
        "/member/checked_in_books.html",
        transactions=transactions,
        TransactionStatus=TransactionStatus,
    )


# member extend book
@app.route("/member/extend")
def member_extend_book():
    trans_id = request.args.get("id")
    transaction = db.transactions.find_one({"_id": ObjectId(trans_id)})
    due_date = transaction["due_date"]
    extended_date = due_date + timedelta(days=14)
    values = {"is_extended": True, "due_date": extended_date}
    result = db.transactions.update_one({"_id": ObjectId(trans_id)}, {"$set": values})
    if result.modified_count > 0:
        flash("Due date extended for two weeks", "success")
    else:
        flash("Error extending due date", "danger")
    return redirect(url_for("member_view_transactions"))


@app.route("/logout/")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)

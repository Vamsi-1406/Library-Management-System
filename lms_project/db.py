from bson import ObjectId
import pymongo

from enums import TransactionStatus

dbClient = pymongo.MongoClient("mongodb://localhost:27017/")
db = dbClient["lms_db"]

admins = db["admins"]
locations = db["locations"]
books = db["books"]
stores = db["stores"]
members = db["members"]
transactions = db["transactions"]
payments = db["payments"]
reserved_books = db["reserved_books"]


faculties = db["Faculties"]
students = db["Students"]
batches = db["Batches"]
project_titles = db["Project_Titles"]
project_Details = db["Project_Details"]
tasks = db["Tasks"]
task_reports = db["TaskReports"]
sub_tasks = db["Sub_Tasks"]
sub_task_reports = db["Sub_TaskReports"]


def isBookTakenByMember(book_id, member_id):
    result = transactions.find_one(
        {
            "book_id": ObjectId(book_id),
            "member_id": ObjectId(member_id),
            "status": TransactionStatus.CHECKED_IN.value,
        }
    )
    if result:
        return True
    else:
        return False


def getBookAvailableDate(book_id):
    result = transactions.find(
        {"book_id": ObjectId(book_id), "status": TransactionStatus.CHECKED_IN.value}
    ).sort("due_date", 1)
    result = list(result)
    if result:
        return result[0]["due_date"]
    else:
        return result

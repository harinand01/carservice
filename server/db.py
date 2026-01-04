"""Database helper module for Car Service and Booking System."""

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "mysql",  # set your MySQL password here if any
    "database": "car_service_db",
}


def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print("[DB] Error while connecting to MySQL:", e)
        raise


def query_one(sql, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        row = cur.fetchone()
        return row
    finally:
        conn.close()


def query_all(sql, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        return rows
    finally:
        conn.close()


def execute(sql, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

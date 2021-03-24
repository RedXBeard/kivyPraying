import os
import sqlite3

from dateutil.parser import parse
from kivy import kivy_home_dir


def full_prayed_dates(max_date=False, min_date=False):
    conn = sqlite3.connect(os.path.join(kivy_home_dir, 'kivypraying.sqlite3'))
    sql = """
        select date, count('id')
        from praying_status 
        where is_prayed
        group by date
        having count('id') = 6
    """
    if min_date:
        sql += """
        order by praying_status.date
        limit 1
        """
    elif max_date:
        sql += """
        order by praying_status.date desc
        limit 1
        """

    cursor = conn.cursor()
    cursor.execute(sql)
    data = cursor.fetchone()
    return parse(data[0]).date()

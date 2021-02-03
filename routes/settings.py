from contextlib import contextmanager
import pymysql
import pandas as pd

# db 연결 정보
HOST = "aihems-service-db.cnz3sewvscki.ap-northeast-2.rds.amazonaws.com"
DB = "aihems_api_db"
PORT = 3306
USER = "aihems"
PASSWORD = "#cslee1234"
CHARSET = "utf8"


@contextmanager
def open_db_connection():
    """Database 연결

    Yields:
        Object: DB Connection Object
    """
    conn = pymysql.connect(
        host=HOST, port=PORT, user=USER, passwd=PASSWORD, db=DB, charset=CHARSET
    )
    try:
        yield conn
    except Exception as err:
        print(err)
    finally:
        conn.close()


def load_datas(query_file, params):
    """쿼리 파일을 읽어와서 해당 데이터를 추출.

    Args:
        query_file (str): sql이 저장된 파일명.
        params (dict): sql에 들어갈 파라미터.

    Returns:
        dataframe: 추출한 데이터
    """
    if not query_file:
        return None

    with open("./queries/" + query_file, "r") as query:
        sql = query.read()

    with open_db_connection() as conn:
        df = pd.read_sql(sql=sql, con=conn, params=params)

    return df


def load_datas_from_csv(csv_file, condition=None):
    """csv에서 데이터를 조회.

    Args:
        csv_file (str): csv 파일
        condition (str, optional): 추출 조건

    Returns:
        dataframe: 추출한 데이터
    """
    df = pd.read_csv("./datas/" + csv_file)

    if condition:
        df.query(condition, inplace=True)

    return df


# if __name__ == '__main__':
#     with open_db_connection() as conn:
#         print(conn)

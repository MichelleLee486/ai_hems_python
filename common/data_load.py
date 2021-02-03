"""학습한 모델을 사용하여 분류/예측을 실행.

전력 사용여부 분류/ 전력 사용량 예측
================================

학습한 모델을 통해 전기기기 일별 전력사용여부를 분류하고
분류한 데이터를 바탕으로 한 가구당 전력 사용량을 예측한다.
"""
import pandas as pd
import numpy as np
import routes.settings as settings
import joblib
from datetime import datetime, timedelta


def split_x_y(df, x_col="", y_col=""):
    """데이터 분리

    Args:
        df (dataframe): 분리할 소스 데이터
        x_col (str, optional): 분리 기준 컬럼명. Defaults to ''.
        y_col (str, optional): 분리 기준 컬럼명. Defaults to ''.

    Returns:
        Array: 기준 컬럼으로 분리한 값
        Array: 기준 컬럼으로 분리한 값
    """
    x = df.loc[:, x_col].values
    y = df.loc[:, y_col].values

    if len(x) == 1:
        x = x.reshape(-1, 1)

    return x, y


def sliding_window_transform(x, y, step_size=10, lag=2, is_training=1):
    """데이터의 형식 변환

    Args:
        x (array): source datas
        y (array): target datas
        step_size (int, optional): sliding window 사이즈. Defaults to 10.
        lag (int, optional): 데이터 변환 시작위치 조정. Defaults to 2.
        is_training (int, optional): 초기 데이터 생성 여부. Defaults to 1.
                0: x의 기본값 미생성
                1: x의 기본값을 step_size만큼 생성

    Returns:
        list: 변환된 source datas
        list: 변환된 target datas
    """
    # 학습데이터의 형태를 확인한 후 데이터를 생성
    n_shape = np.shape(x)

    cols = n_shape[1] if len(n_shape) > 1 else 1

    if is_training:
        x = [[0.0 for i in range(cols)]] * (step_size - 1) + x.tolist()
    else:
        x = x.tolist()

    x_transformed = [
        x[i - step_size + lag : i + lag]
        for i in range(len(x) + 1 - lag)
        if i > step_size - 1
    ]

    x_transformed = np.reshape(x_transformed, (-1, (step_size * cols)))

    return x_transformed, y[:-lag] if lag > 0 else y


def labeling(device_id, gateway_id, collect_date, is_csv=False):
    """디바이스의 일일 전력 사용상태를 분단위로 라벨링

    Args:
        device_id (str): 디바이스ID
        gateway_id (str): 게이트웨이ID
        collect_date (str): 일자
        is_csv (bool, optional): 데이터를 csv 파일에서 조회여부. Defaults to False.

    Returns:
        list: 분단위 전력 사용상태 리스트
    """

    if is_csv:
        # 20분 전 ~ 10분 후의 데이터를 추출하기 위한 조건
        collect_dd = datetime.strptime(collect_date + "000000", "%Y%m%d%H%M%S")
        start_dd = (collect_dd + timedelta(minutes=-20)).strftime("%Y-%m-%d %H:%M:%S")
        end_dd = (collect_dd + timedelta(days=1, minutes=9)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        condition = (
            f"(device_id == '{device_id}') "
            f"and ('{start_dd}' <= collect_dd <= '{end_dd}')"
        )
        df = settings.load_datas_from_csv(
            csv_file="predict/devices.csv", condition=condition
        )
    else:
        df = settings.load_datas(
            query_file="dl_select_labeling.sql",
            params={
                "gateway_id": gateway_id,
                "device_id": device_id,
                "collect_date": collect_date,
            },
        )

    x, y = split_x_y(df, x_col=["energy_diff", "power"], y_col="energy_diff")
    x, y = sliding_window_transform(x, y, step_size=30, lag=10, is_training=0)

    path = f"./pickles/devices/{device_id}.pkl"
    model = joblib.load(path)

    y = model.predict(x).astype(np.int).tolist()

    return y


def predict_elec(house_no, date, is_csv=False):
    """한 가구의 한달 사용전력량을 일별로 예측

    Args:
        house_no (str): 가구식별번호
        date (str): 예측시작일자

    Returns:
        list: 일별 사용전력량
    """

    if is_csv:
        start_dd = (
            (
                datetime.strptime(date, "%Y%m%d").replace(day=1) + timedelta(days=-1)
            ).replace(day=datetime.strptime(date, "%Y%m%d").day)
            + timedelta(days=-7)
        ).strftime("%Y%m%d")

        condition = (
            f"(house_no == '{house_no}') "
            f"and ({int(start_dd)} <= use_date < {int(date)})"
        )

        df = settings.load_datas_from_csv(
            csv_file="predict/houses.csv", condition=condition
        )
    else:
        df = settings.load_datas(
            query_file="dl_select_house.sql",
            params={"house_no": house_no, "date": date},
        )

    # 원-핫-인코딩으로 요일데이터 변경
    columns = [
        "use_energy_daily",
        "dayname_Sunday",
        "dayname_Monday",
        "dayname_Tuesday",
        "dayname_Wednesday",
        "dayname_Thursday",
        "dayname_Friday",
        "dayname_Saturday",
    ]
    df = pd.get_dummies(df)
    df = df.loc[:, columns]

    x, y = split_x_y(df, x_col=columns, y_col="use_energy_daily")
    x, y = sliding_window_transform(x, y, step_size=7, lag=0, is_training=0)

    pd.DataFrame(x).to_csv(
        "./datas/house_pred.csv",
        header=True,
        index=False,
        encoding="utf-8",
    )

    path = f"./pickles/houses/{house_no}.pkl"
    model = joblib.load(path)

    # 7일치의 전력사용량을 기반으로 8일째 전력사용량을 예측
    pred_y = model.predict(x).tolist()

    return pred_y


def check_weeks(device_id, gateway_id):
    """전력사용 로그 테이블의 적재된 기간 확인

    Args:
        device_id (str): 디바이스ID
        gateway_id (str): 게이트웨이ID

    Returns:
        int: 데이터 적재기간(주수)
    """
    sql = f"""
        SELECT
               CEIL(DATEDIFF(NOW(),
                    DATE_FORMAT(min(T.COLLECT_DATE), '%Y%m%d'))/7) AS weeks
          FROM AH_USE_LOG_BYMINUTE T
         WHERE 1 = 1
           AND T.GATEWAY_ID = '{gateway_id}'
           AND T.DEVICE_ID = '{device_id}'
    """
    with settings.open_db_connection() as conn:
        weeks = pd.read_sql(sql, con=conn).loc[0, "weeks"]

    return weeks


if __name__ == "__main__":
    predict_elec(house_no="20180810000008", date="20191201", is_csv=True)
    # check_weeks(device_id="00158D00015095211", gateway_id="ep17470139")
    # labeling(
    #     device_id="000D6F000F745CBD1",
    #     gateway_id="ep18270363",
    #     collect_date="20191106",
    #     is_csv=True,
    # )

"""[summary].

Returns:
    [type]: [description]
"""
import pandas as pd
import numpy as np
import datetime

import routes.settings as settings


def get_one_day_schedule(device_id, gateway_id, dayofweek, collect_date=None):
    """디바이스의 전력 사용여부를 확인하여 해당 요일의 전력 차단 스케줄.

    기준날짜(collect_date)로부터 한달간의 전력사용량을 조회하여
    요일별 전력 차단 스케줄을 조회

    Args:
        device_id (str): 디바이스ID
        gateway_id (str): 게이터웨이ID
        dayofweek (int): 요일 (1:일 2:월 3:화 4:수 5:목 6:금 7:토)
        collect_date (string, optional): 지정일자. Defaults to None.
            지정날짜가 없으면 현재날짜로 설정

    Returns:
        dataframe: 해당 요일의 전력 차단 스케줄
    """
    dayofweek = dayofweek + 1 if dayofweek is not None else 1

    # 디바이스가 항상 켜져 있어야 하는 경우는 모든 시간 사용상태를 1로 반환
    sql = f"""
        SELECT
             IFNULL(T.ALWAYS_ON, 0)  AS always_on
        FROM AH_DEVICE_MODEL T
        WHERE 1 = 1
        AND T.DEVICE_ID  = '{device_id}'
    """
    with settings.open_db_connection() as conn:
        always_on = pd.read_sql(sql, con=conn).loc[0, "always_on"]

    if always_on == 1:
        df = pd.DataFrame(
            [[str(dayofweek), "00:00:00", "23:59:00", "1439", "1"]],
            columns=[
                "dayofweek",
                "start",
                "end",
                "duration",
                "status",
            ],
        )

        return df

    # 지정된 일자가 없으면 현재 날짜로 지정
    collect_date = (
        collect_date
        if collect_date
        else datetime.datetime.now().strftime("%Y%m%d")
    )

    sql = f"""
        SELECT
              T.DAY_NM            AS day_nm
            , T.COLLECT_DD        AS curr_dt
            , T.COLLECT_DATE      AS curr_dd
            , T.APPLIANCE_STATUS  AS status
        FROM (
              SELECT
                      STR_TO_DATE(CONCAT(T.COLLECT_DATE
                                       , T.COLLECT_TIME)
                                , '%Y%m%d%H%i')         AS COLLECT_DD
                    , DAYOFWEEK(T.COLLECT_DATE)         AS DAY_NM
                    , T.COLLECT_DATE
                    , T.ENERGY_DIFF
                    , IFNULL(T.APPLIANCE_STATUS, 0)     AS APPLIANCE_STATUS
                FROM AH_USE_LOG_BYMINUTE T
               WHERE 1=1
                 AND T.GATEWAY_ID = '{gateway_id}'
                 AND T.DEVICE_ID = '{device_id}'
                 AND T.COLLECT_DATE >= DATE_FORMAT(
                                        DATE_ADD(
                                            STR_TO_DATE('{collect_date}'
                                                       , '%Y%m%d')
                                          , INTERVAL -28 DAY)
                                       , '%Y%m%d')
                AND T.COLLECT_DATE < '{collect_date}'
            ) T
        WHERE 1=1
          AND T.DAY_NM = '{dayofweek}'
        ORDER BY
              T.COLLECT_DD
    """

    with settings.open_db_connection() as conn:
        df = pd.read_sql(sql, con=conn)

    if sum(df.status.apply(lambda x: int(x))) == 0:
        return pd.DataFrame(
            [[str(dayofweek), "00:00:00", "23:59:00", "1439", "0"]],
            columns=[
                "dayofweek",
                "start",
                "end",
                "duration",
                "status",
            ],
        )

    # 데이터 전처리 ############################################################
    # 가전기구 사용/대기 상태를 1분전 상태와 비교하여 상태가
    # 다를경우(ON->OFF, OFF->ON)일 경우만 추출
    # 60분이상 미사용상태이거나 30분이상 사용상태일 경우만 추출하여
    # 요일별 시간대별로 사용 대기 상태를 추출한다.
    df["pre_status"] = df.groupby(by=["curr_dd"], dropna=False)[
        "status"
    ].shift(periods=1, fill_value=0)

    diff = df.query("pre_status != status").reset_index(drop=True)

    diff.insert(
        loc=len(diff.columns),
        column="start",
        value=diff["curr_dt"].shift(1).fillna(pd.to_datetime(diff["curr_dd"])),
    )

    diff.insert(
        loc=len(diff.columns),
        column="duration",
        value=(diff["curr_dt"] - diff["start"]).apply(
            lambda x: x.seconds / 60
        ),
    )

    diff = diff.loc[
        :, ["day_nm", "start", "curr_dt", "duration", "pre_status"]
    ].rename(
        columns={
            "curr_dt": "end",
            "pre_status": "status",
            "day_nm": "dayofweek",
        }
    )
    # 60분이상 미사용상태이거나 30분이상 사용상태일 경우만 추출
    diff.query(
        "index == 0 | (duration >= 60 & status == 0) "
        "| (duration >= 30 & status == 1)",
        inplace=True,
    )

    diff["start_tm"] = diff["start"].apply(lambda x: str(x).split()[1])

    diff = diff.sort_values("start_tm").reset_index(drop=True)
    # 해당 시간에 상태가 중복되면 상태 1(on)이 우선권을 가짐
    diff.insert(
        loc=len(diff.columns),
        column="rnk",
        value=diff.groupby(by=["start_tm"])["status"].rank(
            ascending=False, method="first"
        ),
    )

    diff.query("rnk == 1", inplace=True)
    # 연속되는 상태를 제거
    diff.insert(
        loc=len(diff.columns),
        column="pre_status",
        value=diff["status"].shift(1),
    )

    diff = (
        diff.query("status != pre_status", inplace=False)
        .drop(columns=["rnk", "pre_status"])
        .reset_index(drop=True)
    )

    diff.insert(
        loc=len(diff.columns),
        column="end_tm",
        value=diff["start_tm"]
        .shift(-1)
        .apply(
            lambda x: str(x + pd.Timedelta(seconds=-60)).split()[2]
            if x is not np.nan
            else "23:59:00"
        ),
    )

    diff["duration"] = (
        pd.to_datetime(diff["end_tm"], format="%H:%M:%S")
        - pd.to_datetime(diff["start_tm"], format="%H:%M:%S")
    ).dt.total_seconds() / 60
    # 데이터 전처리 #############################################################

    df = diff.loc[
        :, ["dayofweek", "start_tm", "end_tm", "duration", "status"]
    ].rename(columns={"start_tm": "start", "end_tm": "end"})

    return df


def get_ai_schedule(device_id, gateway_id):
    """디바이스의 요일별 스케줄 조회.

    Args:
        device_id (str): 디바이스ID
        gateway_id (str): 게이트웨이ID

    Returns:
        dataframe: 요일별 전력 차단 스케줄 조회
    """
    df = pd.DataFrame(
        columns=["dayofweek", "start", "end", "duration", "status"]
    )

    for i in range(7):
        tmp = get_one_day_schedule(
            device_id=device_id, gateway_id=gateway_id, dayofweek=i
        )

        df = pd.concat([df, tmp], ignore_index=True)

    return df.loc[:, ["dayofweek", "start", "end", "duration", "status"]]


# if __name__ == '__main__':
# get_ai_schedule(device_id='00158D00015095211', gateway_id='ep17470139')

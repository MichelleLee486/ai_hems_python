"""[summary]

Returns:
    [type]: [description]
"""
import pandas as pd
import routes.settings as settings


def cbl_info(house_no, request_dr_no):
    """CBL 산출

    Args:
        house_no (str): 가구식별번호
        request_dr_no (str): 요청DR식별번호

    Returns:
        float: CBL
        float: 전력절감량
    """
    sql = f"""
        SELECT
             AVG(T.SUM_ENERGY) AS energy_avg
        FROM (
            SELECT
                  T.COLLECT_DATE
                , SUM(T.ENERGY_DIFF)  AS SUM_ENERGY
            FROM (
                    SELECT
                          T.COLLECT_DATE
                        , T.COLLECT_TIME
                        , DAYOFWEEK(T.COLLECT_DATE) AS DAY_NM
                        , T.ENERGY_DIFF
                    FROM AH_USE_LOG_BYMINUTE T
                    INNER JOIN AH_GATEWAY_INSTALL S
                        ON (S.GATEWAY_ID = T.GATEWAY_ID)
                    WHERE 1 = 1
                    AND S.HOUSE_NO  = '{house_no}'
                    ) T
            INNER JOIN (
                    SELECT
                          DATE_FORMAT(DATE_ADD(START_DATE, INTERVAL -7 DAY)
                                    , '%Y%m%d')             AS START_DATE
                        , DATE_FORMAT(DATE_ADD(START_DATE, INTERVAL -1 DAY)
                                    , '%Y%m%d')             AS END_DATE
                        , DATE_FORMAT(START_DATE, '%H%i')   AS START_TIME
                        , DATE_FORMAT(END_DATE, '%H%i')     AS END_TIME
                    FROM AH_DR_REQUEST R
                    WHERE 1 = 1
                    AND R.REQUEST_DR_NO = '{request_dr_no}'
                ) R
                ON ( T.COLLECT_DATE BETWEEN R.START_DATE AND R.END_DATE
                AND T.COLLECT_TIME BETWEEN R.START_TIME AND R.END_TIME )
            WHERE 1 = 1
            AND T.DAY_NM BETWEEN 2 AND 6
            GROUP BY
                  T.COLLECT_DATE
                , T.DAY_NM
            ORDER BY
                  SUM_ENERGY DESC
            LIMIT 4
        ) T
    """

    with settings.open_db_connection() as conn:
        cbl = pd.read_sql(sql, con=conn).iloc[0]["energy_avg"]

    if cbl <= 500:
        reduction_energy = cbl * 0.3
    elif cbl <= 1500:
        reduction_energy = cbl * 0.15 + 75
    else:
        reduction_energy = 300

    return cbl, reduction_energy


def get_dr_recommandation(house_no, request_dr_no):
    """요청DR시간대에 참여할 디바이스 추천

    Args:
        house_no (str): 가구식별번호
        request_dr_no (str): 요청DR번호

    Returns:
        boolean: DR참여여부
        float: CBL값
        float: 에너지 절감량
        dictionary: DR참여 추천 디바이스

    """
    cbl, reduction_energy = cbl_info(
        house_no=house_no, request_dr_no=request_dr_no
    )
    # 소켓이 항상 켜져있고, 사용 빈도가 작은데 소비량이 많은 경우
    sql = f"""
        SELECT
              T.GATEWAY_ID                                     AS gateway_id
            , T.DEVICE_ID                                      AS device_id
            , T.FREQUENCY                                      AS frequency
            , (SUM(H.WAIT_ENERGY) / SUM(H.WAIT_TIME)) * T.DIFF AS energy_wait
            , (SUM(H.USE_ENERGY) / SUM(H.USE_TIME))   * T.DIFF AS energy_use
            , IF(SUM(S.ONOFF) > 2.5, 1, 0)                     AS onoff
            , IF(AVG(S.POWER) > 0.5, 1, 0)                     AS status
            , IFNULL(IF(AVG(S.POWER) > 0.5
                       , SUM(H.USE_ENERGY) / SUM(H.USE_TIME)
                       , SUM(H.WAIT_ENERGY) / SUM(H.WAIT_TIME))
                    , 0)                                       AS energy
        FROM (
                SELECT
                      T.GATEWAY_ID
                    , T.DEVICE_ID
                    , T.DIFF
                    , SUM(T.APPLIANCE_STATUS)  AS FREQUENCY
                FROM (
                        SELECT
                              L.GATEWAY_ID
                            , L.DEVICE_ID
                            , L.COLLECT_DATE
                            , R.DIFF
                            , MAX(IFNULL(L.APPLIANCE_STATUS, 0))
                                                    AS APPLIANCE_STATUS
                          FROM AH_GATEWAY_INSTALL G
                         INNER JOIN AH_USE_LOG_BYMINUTE L
                            ON (L.GATEWAY_ID = G.GATEWAY_ID)
                         INNER JOIN AH_DEVICE D
                            ON (D.DEVICE_ID = L.DEVICE_ID)
                         INNER JOIN (
                                SELECT
                                      DAYOFWEEK(R.START_DATE)           AS DAY_NM
                                    , DATE_FORMAT(R.START_DATE, '%H%i') AS START_TIME
                                    , DATE_FORMAT(R.END_DATE, '%H%i')   AS END_TIME
                                    , TIMESTAMPDIFF(MINUTE
                                                  , R.START_DATE
                                                  , R.END_DATE)         AS DIFF
                                 FROM AH_DR_REQUEST R
                                WHERE 1 = 1
                                  AND R.REQUEST_DR_NO = '{request_dr_no}'
                            ) R
                            ON ( R.DAY_NM = DAYOFWEEK(L.COLLECT_DATE)
                             AND L.COLLECT_TIME BETWEEN R.START_TIME
                                                    AND R.END_TIME )
                        WHERE 1 = 1
                          AND G.HOUSE_NO = '{house_no}'
                          AND D.FLAG_USE_AI = 'Y'
                        GROUP BY
                              L.GATEWAY_ID
                            , L.DEVICE_ID
                            , L.COLLECT_DATE
                            , R.DIFF
                    ) T
                WHERE 1 = 1
                GROUP BY
                      T.GATEWAY_ID
                    , T.DEVICE_ID
                    , T.DIFF
            ) T
        INNER JOIN AH_DEVICE_ENERGY_HISTORY H
           ON ( H.GATEWAY_ID = T.GATEWAY_ID
            AND H.DEVICE_ID = T.DEVICE_ID )
        INNER JOIN aihems_service_db.AH_LOG_SOCKET S
          ON ( S.GATEWAY_ID = T.GATEWAY_ID
            AND S.DEVICE_ID  = T.DEVICE_ID
            AND S.COLLECT_DATE = DATE_FORMAT(NOW(), '%Y%m%d'))
            AND S.COLLECT_TIME >= DATE_FORMAT(
                                    DATE_ADD(
                                        DATE_ADD(NOW(), INTERVAL 9 HOUR)
                                      , INTERVAL -5 MINUTE)
                                  , '%H%i'))
        WHERE 1 = 1
        GROUP BY
              T.GATEWAY_ID
            , T.DEVICE_ID
            , T.FREQUENCY
        ORDER BY
              STATUS DESC
            , ONOFF DESC
            , FREQUENCY ASC
            , ENERGY DESC
    """

    with settings.open_db_connection() as conn:
        df = pd.read_sql(sql, con=conn)

    df["energy_sum"] = df.apply(
        lambda x: max(x["energy_use"], x["energy_wait"]), axis=1
    )
    df["energy_cusum"] = df["energy_sum"].cumsum()
    df["permission"] = df.apply(
        lambda x: x["energy_cusum"] < (cbl - reduction_energy), axis=1
    )
    df["energy_sum"] = df.apply(lambda x: str(x.energy_sum), axis=1)

    df = df.loc[:, ["device_id", "energy_sum", "permission"]]

    dr_success = bool(df.loc[0, "permission"])
    recommendation = df.to_dict("index") if dr_success else "0"

    return dr_success, cbl, reduction_energy, recommendation


# if __name__ == '__main__':
# cbl_info(house_no='20181203000013', request_dr_no='2019102101')
# get_dr_recommandation(house_no='20180810000001', request_dr_no='2019102101')

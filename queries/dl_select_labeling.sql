SELECT
       T.GATEWAY_ID     AS gateway_id
     , T.DEVICE_ID      AS device_id
     , T.ENERGY_DIFF    AS energy_diff
     , T.COLLECT_DD     AS collect_dd
     , T.POWER          AS power
     , T.ONOFF          AS onoff
  FROM (
    SELECT
           T.GATEWAY_ID
         , T.DEVICE_ID
         , T.ENERGYU
         , T.ENERGY_DIFF
         , T.POWER
         , T.ONOFF
         , STR_TO_DATE(CONCAT(T.COLLECT_DATE, T.COLLECT_TIME), '%%Y%%m%%d%%H%%i') AS COLLECT_DD
      FROM AH_USE_LOG_BYMINUTE T
     WHERE 1 = 1
      AND T.GATEWAY_ID  = %(gateway_id)s
      AND T.DEVICE_ID   = %(device_id)s
    ) T
 WHERE 1 = 1
   AND COLLECT_DD BETWEEN DATE_ADD(STR_TO_DATE(CONCAT(%(collect_date)s, '0000'), '%%Y%%m%%d%%H%%i')
                                , INTERVAL -20 MINUTE)
                      AND DATE_ADD(STR_TO_DATE(CONCAT(%(collect_date)s, '2359'), '%%Y%%m%%d%%H%%i')
                                , INTERVAL +10 MINUTE)
 ORDER BY
       T.GATEWAY_ID
     , T.DEVICE_ID
     , T.COLLECT_DD
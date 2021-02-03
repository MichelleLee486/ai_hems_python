SELECT
       T.house_no
     , T.use_date
     , T.use_energy_daily
     , T.dayname
  FROM (
    SELECT
           G.HOUSE_NO                AS house_no
         , T.COLLECT_DATE            AS use_date
         , SUM(T.ENERGY_DIFF)        AS use_energy_daily
         , DAYNAME(T.COLLECT_DATE)   AS dayname
      FROM AH_USE_LOG_BYMINUTE T
     INNER JOIN AH_GATEWAY_INSTALL G
        ON (G.GATEWAY_ID = T.GATEWAY_ID)
     WHERE 1 = 1
       AND G.HOUSE_NO = %(house_no)s
       AND T.COLLECT_DATE >= DATE_FORMAT(DATE_ADD(DATE_ADD(STR_TO_DATE(%(date)s, '%%Y%%m%%d')
                                                         , INTERVAL -1 MONTH)
                                                , INTERVAL -7 DAY)
                                        , '%%Y%%m%%d')
       AND T.COLLECT_DATE < %(date)s
     GROUP BY
           G.HOUSE_NO
         , T.COLLECT_DATE
    ) T
ORDER BY
     house_no
   , use_date
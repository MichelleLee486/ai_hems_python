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
 GROUP BY
       G.HOUSE_NO
     , T.COLLECT_DATE

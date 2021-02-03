SELECT 
       T.GATEWAY_ID  AS gateway_id
     , T.DEVICE_ID   AS device_id
     , T.ENERGY      AS energy
     , T.ENERGY_DIFF AS energy_diff
     , T.POWER       AS power
     , T.ONOFF       AS onoff
     , IFNULL(T.APPLIANCE_STATUS, 0) AS appliance_status
  FROM AH_DEVICE_INSTALL D
 INNER JOIN AH_USE_LOG_BYMINUTE T 
    ON ( T.GATEWAY_ID = D.GATEWAY_ID
     AND T.DEVICE_ID  = D.DEVICE_ID )
 INNER JOIN (
    SELECT 
           T.GATEWAY_ID
         , T.DEVICE_ID
         , T.COLLECT_DATE
      FROM AH_USE_LOG_BYMINUTE T
     WHERE 1 = 1
       AND T.DEVICE_ID = %(device_id)s
       AND T.APPLIANCE_STATUS IS NOT NULL
     GROUP BY 
           T.GATEWAY_ID
         , T.DEVICE_ID
         , T.COLLECT_DATE
    ) S 
   ON ( T.COLLECT_DATE = S.COLLECT_DATE
    AND T.GATEWAY_ID   = S.GATEWAY_ID
    AND T.DEVICE_ID    = S.DEVICE_ID )
WHERE 1 = 1
    AND D.DEVICE_ID = %(device_id)s
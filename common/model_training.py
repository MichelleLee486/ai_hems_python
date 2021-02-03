"""분류,예측모델 학습

전력 사용여부 분류, 전력 사용량 예측 모델 학습
==================
가전기기별 전력사용정보를 통해 분당 전력사용여부 분류모델을 학습,
이를 바탕으로 가구별 전력사용량 예측모델을 학습한다.

"""
from sklearn import model_selection
import pandas as pd
import joblib

from routes import settings, classifications
import common.data_load as dl
import numpy as np


def make_model_status(device_id, model_type="random forest", lag=10, is_csv=False):
    """디바이스의 대기/사용 라벨링에 대한 예측모델학습

    모델은 Random forast 방식을 사용한다.
    기본은 한달 사용량이상 적재되면 모델을 학습시킨다.
    x: 전력사용차(energy_diff), 순시전력(power), on/off(onoff) 등
    y: 사용/대기 상태

    Args:
      device_id (str): 디바이스ID
      model_type (str, optional): 모델 타입. Defaults to 'random forest'
              random forest / xgboost classifier
      lag (int, optional): 데이터 시작점 이동범위. Defaults to 10.
      is_csv (bool, optional): 데이터를 csv 파일에서 조회여부. Defaults to False.

    Returns:
      str: 학습모델 저장경로
      float: 교차검증점수
    """

    if is_csv:
        condition = f"device_id == '{device_id}'"
        df = settings.load_datas_from_csv(
            csv_file="training/devices.csv", condition=condition
        )
    else:
        df = settings.load_datas(
            query_file="mt_select_device.sql", params={"device_id": device_id}
        )

    x, y = dl.split_x_y(df, x_col=["energy_diff", "power"], y_col="appliance_status")
    # 30분 단위로 sliding
    x, y = dl.sliding_window_transform(x, y, step_size=30, lag=lag)

    # 확인 #####################################################################
    # x_train, x_test, y_train, y_test = model_selection.train_test_split(
    #                                               x,
    #                                               y,
    #                                               test_size = 0.25,
    #                                               random_state = 10)
    # if model_type == 'random forest':
    #   rf = ensemble.RandomForestClassifier(random_state=0)
    # else:
    #   rf = XGBClassifier(n_estimators=50,
    #                     max_depth=8,
    #                     objective='binary:logistic',
    #                     verbosity=0)
    #
    # rf.fit(x_train, y_train)
    # pred = rf.predict(x_test)
    # print(metrics.accuracy_score(y_test, pred))
    # ##########################################################################

    model, params = classifications.select_classification_model(model_type)

    gs = model_selection.GridSearchCV( 
        estimator=model,
        param_grid=params,
        cv=5,
        scoring="accuracy",
        n_jobs=-1,
    )

    gs.fit(x, y)

    path = f"./pickles/devices/{device_id}.pkl"
    joblib.dump(gs, path)

    return path, gs.best_score_


def make_model_elec(house_no, model_type="linear regression", is_csv=False):
    """가구의 전력사용량 예측모델 학습

    가구의 한달 사용전력량으로 다음달의 전력 사용량 예측 모델 학습
    예측모델은 liner regression(선형회귀)를 사용한다.
    7일치 데이터를 기반으로 8일째 되는 데이터를 예측한다.

    Args:
      house_no (str): 가구식별번호
      model_type (str, optional): 모델 타입. Defaults to 'linear regression'.
      is_csv (bool, optional): 데이터를 csv 파일에서 조회여부. Defaults to False.

    Returns:
      float: 교차검증점수
    """
    # 로그데이터를 조회하여 사용하도록 수정
    # 에너지 사용량, 요일을 같이 변수로 사용
    if is_csv:
        condition = f"house_no == '{house_no}'"
        df = settings.load_datas_from_csv(
            csv_file="training/houses.csv", condition=condition
        )
    else:
        df = settings.load_datas(
            query_file="mt_select_house.sql", params={"house_no": house_no}
        )

    # 예측할 일자의 앞 일자를 설정
    # 7일치를 기반으로 예측
    step_size = 7
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

    x, y = dl.split_x_y(df, x_col=columns, y_col="use_energy_daily")
    x, y = dl.sliding_window_transform(x, y, step_size=step_size, lag=0)

    c = pd.merge(
        pd.DataFrame(x[(step_size - 1) : -1]),
        pd.DataFrame(y[step_size:]),
        left_index=True,
        right_index=True,
        how="left",
    )

    c.to_csv(
        "./datas/house_trainig.csv",
        header=True,
        index=False,
        encoding="utf-8",
    )

    # 선형회귀 검증 ############################################################
    # if model_type == "linear regression":
    #     reg = linear_model.LinearRegression()
    # else:
    #     reg = XGBRegressor()

    # reg.fit(x[(step_size-1):-1], y[step_size:])

    # y_pred = reg.predict(x)
    # print('Mean squared error: %.2f' % metrics.mean_squared_error(y, y_pred))
    # # The coefficient of determination: 1 is perfect prediction
    # print('Coefficient of determination: %.2f' % metrics.r2_score(y, y_pred))
    ###########################################################################

    model, params = classifications.select_classification_model(model_type)

    gs = model_selection.GridSearchCV(
        estimator=model,
        param_grid=params,
        cv=5,
        n_jobs=-1,
    )
    gs.fit(x[(step_size - 1) : -1], y[step_size:])

    path = f"./pickles/houses/{house_no}.pkl"
    joblib.dump(gs, path)

    return gs.best_score_


if __name__ == "__main__":
    # make_model_status(
    #     device_id="00158D000151B1FB1", model_type="xgboost classifier", is_csv=True
    # )
    make_model_elec(house_no="20180810000008", is_csv=False)

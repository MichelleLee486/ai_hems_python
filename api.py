"""전력량 예측 API

 API
==========

스마트 플러그로 수집한 데이터를 기반으로 각 가정의 가전기기들 전력 사용상태를
분류하고월별 전력사용량을 예측한다.
또한, 요일별 가전기기의 전력사용현황을 집계하여 요일별 전력 절감을 위한 차단
스케줄을 생성한다.
그리고 사용자에게 CBL, 전력 절감량을 제시하여 전력절감에 도움을 준다.
"""

from flask import Flask, request, jsonify
from flask_restful import Api

import common.model_training as mt
import common.data_load as dl
import common.ai as ai
import common.dr as dr

app = Flask(__name__)
api = Api(app)


@app.route("/make_model_status", methods=["POST"])
def make_model_status():
    """디바이스 전력사용상태 분류모델 학습
    분류모델: Random Forest(default)
             XBGboost: 2020.12.24 채택

        Input example:
            {"device_id" : "000D6F000F745CBD1", "is_csv":true}
            is_csv : false => 데이터베이스 사용

    Returns:
        string: 분류모델 정보

        Output example:
            {
                "dump_path": "./pickles/devices/000D6F000F745CBD1.pkl",
                "flag_success": true,
                "score": "0.9977365841899287"
            }
    """
    try:
        device_id = request.json["device_id"]
        # csv를 사용여부를 확인. is_csv의 기본값은 데이터베이스사용(is_csv=Flase)
        try:
            is_csv = request.json["is_csv"]
        except KeyError:
            is_csv = False

        # model_type: random forest, xgboost classifier
        path, score = mt.make_model_status(
            device_id=device_id, model_type="xgboost classifier", is_csv=is_csv
        )

        return jsonify(
            {
                "flag_success": True,
                "dump_path": str(path),
                "score": str(score),
            }
        )
    except Exception as ex:
        return jsonify({"flag_success": False, "error": str(ex)})


@app.route("/make_model_elec", methods=["POST"])
def make_model_elec():
    """가구 전력 사용량 예측모델 학습
    예측모델: Linear Regression(default): 2020.12.24 채택
             XGBboost

        POST example:
            {"house_no":"20190325000002", "is_csv":true}
            is_csv : false => 데이터베이스 사용

    Returns:
        string: 예측모델 정보

        Output example:
            {
                "best_score": "-410.1643493708034",
                "flag_success": true
            }
    """
    try:
        house_no = request.json["house_no"]
        # csv를 사용여부를 확인. is_csv의 기본값은 데이터베이스사용(is_csv=Flase)
        try:
            is_csv = request.json["is_csv"]
        except KeyError:
            is_csv = False

        # model_type: linear regression, xgboost regressor
        score = mt.make_model_elec(house_no=house_no, is_csv=is_csv)

        return jsonify({"flag_success": True, "best_score": str(score)})
    except Exception as ex:
        return jsonify({"flag_success": False, "error": str(ex)})


@app.route("/label", methods=["POST"])
def label():
    """디바이스의 하루 전력 사용상태 라벨링
    미리 학습된 디바이스별 분류모델을 사용

        Input example:
            {
                "device_id" : "000D6F000F745CBD1",
                "gateway_id": "ep18270363",
                "collect_date":"20191106",
                "is_csv":true
            }
            is_csv : false => 데이터베이스 사용

    Returns:
        string: 분당 전력 사용상태

        Output example:
            {
                "flag_success": true,
                "predicted_status": [
                    0,
                    0,
                    ...
                ]
            }
    """
    try:
        device_id = request.json["device_id"]
        gateway_id = request.json["gateway_id"]
        collect_date = request.json["collect_date"]

        # csv를 사용여부를 확인. is_csv의 기본값은 데이터베이스사용(is_csv=Flase)
        try:
            is_csv = request.json["is_csv"]
        except KeyError:
            is_csv = False

        pred_y = dl.labeling(
            device_id=device_id,
            gateway_id=gateway_id,
            collect_date=collect_date,
            is_csv=is_csv,
        )

        return jsonify({"flag_success": True, "predicted_status": pred_y})
    except Exception as ex:
        return jsonify({"flag_success": False, "error": str(ex)})


@app.route("/elec", methods=["POST"])
def elec():
    """가구의 한달동안의 사용전력량 예측

        Input example:
            {
                "house_no":"20190325000002",
                "date":"20191201",
                "is_csv":true
            }
            is_csv : false => 데이터베이스 사용

    Returns:
        string: 일별 전력사용량

        Out example:
            {
                "flag_success": true,
                "predict_use_energy": [
                    "20774.558479189993",
                    "20473.863460329412",
                    ...
                    "6390.184965580584"
                ]
            }
    """
    try:
        house_no = request.json["house_no"]
        date = request.json["date"]

        # csv를 사용여부를 확인. is_csv의 기본값은 데이터베이스사용(is_csv=Flase)
        try:
            is_csv = request.json["is_csv"]
        except KeyError:
            is_csv = False

        pred_y = list(
            map(str, dl.predict_elec(house_no=house_no, date=date, is_csv=is_csv))
        )

        return jsonify({"flag_success": True, "predict_use_energy": pred_y})
    except Exception as ex:
        return jsonify({"flag_success": False, "error": str(ex)})


@app.route("/schedule", methods=["POST"])
def ai_schedule():
    """디바이스의 요일별 차단 차단 스케줄을 반환

    Returns:
        string: 요일별 전력 차단 스케줄을 JSON형식으로 반환
    """
    try:
        device_id = request.json["device_id"]
        gateway_id = request.json["gateway_id"]

        weeks = dl.check_weeks(device_id, gateway_id)

        if weeks < 4:
            return jsonify(
                {
                    "flag_success": False,
                    "error": "Not enough Log data",
                }
            )

        elec_df = ai.get_ai_schedule(device_id, gateway_id)
        elec_df.columns = [
            "dayofweek",
            "time",
            "end",
            "duration",
            "appliance_status",
        ]
        df_elec = elec_df.loc[:, ["dayofweek", "time", "appliance_status"]].to_dict(
            "index"
        )

        return jsonify(
            {
                "flag_success": True,
                "device_id": device_id,
                "result": df_elec,
            }
        )
    except Exception as ex:
        return jsonify({"flag_success": False, "error": str(ex)})


@app.route("/cbl_info", methods=["POST"])
def cbl_info():
    """DR요청시간대의 CBL 정보

    Returns:
        string: CBL, 전력 절감량
    """
    try:
        house_no = request.json["house_no"]
        request_dr_no = request.json["request_dr_no"]

        cbl, reduction_energy = dr.cbl_info(
            house_no=house_no, request_dr_no=request_dr_no
        )

        return jsonify(
            {
                "flag_success": True,
                "cbl": cbl,
                "reduction_energy": reduction_energy,
            }
        )
    except Exception as ex:
        return jsonify({"flag_success": False, "error": str(ex)})


@app.route("/dr_recommandation", methods=["POST"])
def dr_recommandation():
    """DR요청시간대에 참여 디바이스 추천

    Returns:
        string: DR 참여 추천 디바이스 정보
    """
    try:
        house_no = request.json["house_no"]
        request_dr_no = request.json["request_dr_no"]

        (
            dr_success,
            cbl,
            reduction_energy,
            recommendation,
        ) = dr.get_dr_recommandation(house_no=house_no, request_dr_no=request_dr_no)

        return jsonify(
            {
                "flag_success": True,
                "dr_success": dr_success,
                "cbl": str(cbl),
                "reduction_energy": str(reduction_energy),
                "recommendation": recommendation,
            }
        )
    except Exception as ex:
        return jsonify({"flag_success": False, "error": str(ex)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=True)
    # make_model_status(device_id='00158D0001A457111')

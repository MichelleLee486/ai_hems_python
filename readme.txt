############################################
# 설치 가이드                               #
############################################
1. Python 3.7 버전 권장 
    (3.8 버전이상일 경우 일부 패키지 등이 제대로 실행되지 않을 수 있음)

2. 프로젝트내에 가상환경을 설정해 실행하는 것을 권장

    usage example: 
        * 설치 
            root> python -m venv example(생성할 폴더이름)
        * 실행
            root> cd example 
            root\example> Scripts\activate
            (example) root\example>
        * 종료
            (example) root\example> Scripts\deactivate

3. 패키지는 requirments.txt에 설정된 것을 사용하는 것을 권장   

    usage example:
        * 패키지 설치
            (example) root> pip install -r requirments.txt
        * 위의 명령어 실행으로 설치가 되지 않을 경우는 개별적으로 설치
            (example) root> pip install numpy==1.19.3

############################################
# 사용 가이드                               #
############################################
flask로 작성된 API 이므로 프로젝트 실행 후 POSTMAN을 통해 테스트

    usage example:
        * 프로젝트 실행
            (example) root>python api.py
             * Serving Flask app "api" (lazy loading)
             * Environment: production
             * Debug mode: on
             * Restarting with stat
             * Debugger is active!
             * Debugger PIN: 204-358-173
             * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
        * Postman을 설치한 후 해당 프로그램을 통해 호출
            Postman 다운로드 url: https://www.postman.com/downloads/

            Postman을 실행한 후 프로젝트 실행시 출력한 url을 호출
                Type: POST
                URL : http://127.0.0.1:5000/

        * api에 작성한 url 호출시 body에 필요한 변수값을 JSON형식으로 작성 
                Type: POST
                URL : http://127.0.0.1:5000/make_model_status
                Body : {"device_id":"00158D00015095211"}
                Body Type: JSON(application/json)
        * Send를 클릭하면 프로젝트의 해당 함수를 호출한 후 반환값을 Postman 하단의 
          Body에 표시
                {
                    "dump_path": "./pickles/devices/00158D00015095211.pkl",
                    "flag_success": true,
                    "score": "0.926805065203736"
                }

############################################
# 개발 이력                                 #
############################################
[2020.12.24]
    1. TODO fix 완료
    2. Docstring 표준 적용
[2020.12.23]
    1. 현행코드 개선 완료
        - 분류모델 (random forest, XGBoost)
        - 예측모델 (linear regression, XGBoost)
        - 모델 예측시 변수를 여러개 설정할 수 있도록 수정
        - SQL 수정 및 재작성 
    2. Python 코드 작성 표준 가이드 적용
    3. TODO 수정 필요 
        - 모델 학습, 예측시 사용한 로그 테이블 변경 필요
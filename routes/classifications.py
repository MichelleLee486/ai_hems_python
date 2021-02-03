from sklearn import ensemble, linear_model
import lightgbm as lgb
import xgboost as xgb


def select_classification_model(model_name):
    """모델의 설정값을 반환

    Args:
        model_name (string): 모델명
            randam forest
            xgboost classifier
            xgboost regressor
            lightgbm classifier
            lightgbm regression
            linear regression

    Returns:
        Class: 모델
        dictionary: 파라미터 정보
    """
    classification = {
        "random forest": [
            ensemble.RandomForestClassifier(),
            {
                "n_estimators": [10],
                "criterion": ["gini"],
                "max_depth": [None],
                "min_samples_split": [2],
                "min_samples_leaf": [1],
                "min_weight_fraction_leaf": [0.0],
                "max_features": ["auto"],
                "max_leaf_nodes": [None],
                "min_impurity_decrease": [0.0],
                # 'min_impurity_split': [0],
                "bootstrap": [True],
                "oob_score": [False],
                "n_jobs": [None],
                "random_state": [None],
                "verbose": [0],
                "warm_start": [False],
                "class_weight": [None],
            },
        ],
        "xgboost classifier": [
            xgb.XGBClassifier(),
            {
                "booster": ["gbtree"],
                "verbosity": [0],
                "max_depth": [8],
                "min_child_weight": [1],
                "gamma": [0],
                "nthread": [4],
                "colsample_bytree": [0.5],
                "colsample_bylevel": [0.9],
                # 'min_impurity_split': [0],
                "n_estimators": [50],
                "objective": ["binary:logistic"],
                "random_state": [None],
                "use_label_encoder": [False],
                # 'warm_start': [False],
                # 'class_weight': [None],
            },
        ],
        "xgboost regressor": [
            xgb.XGBRegressor(),
            {
                "nthread": [4],
                "objective": ["reg:linear"],
                "learning_rate": [0.03, 0.05, 0.07],
                "max_depth": [5, 6, 7],
                "min_child_weight": [4],
                "verbosity": [0],
                "subsample": [0.7],
                "colsample_bytree": [0.7],
                "n_estimators": [500],
            },
        ],
        "lightgbm classifier": [
            lgb.LGBMClassifier(),
            {
                "learning_rate": [0.005, 0.01],
                "n_estimators": [8, 16, 24],
                "num_leaves": [6, 8, 12, 16],
                "boosting_type": ["gbdt", "dart"],
                "objective": ["binary"],
                "max_bin": [255, 510],
                # 'random_state': [500],
                "colsample_bytree": [0.64, 0.65, 0.66],
                "subsample": [0.7, 0.75],
                # 'min_impurity_split': [0],
                "reg_alpha": [1, 1.2],
                "reg_lambda": [1, 1.2, 1.4],
                "random_state": [None],
                # 'verbose': [0],
                # 'warm_start': [False],
                # 'class_weight': [None],
            },
        ],
        "lightgbm regression": [
            lgb.LGBMRegressor(),
            {
                "learning_rate": [0.3],
                "boosting_type": ["gbdt"],
                "objective": ["binary"],
                "metric": ["binary_logloss"],
                "sub_feature": [0.5],
                "num_leaves": [10],
                "min_data": [50],
                "max_depth": [10],
                "verbosity": [-1],
            },
        ],
        "linear regression": [
            linear_model.LinearRegression(),
            {
                "fit_intercept": [True],
                "normalize": [False],
                "copy_X": [True],
                "n_jobs": [None],
            },
        ],
    }

    return classification[model_name][0], classification[model_name][1]


# if __name__ == '__main__':
#     model, params = select_classification_model('random forest')
#     print(type(model), type(params))

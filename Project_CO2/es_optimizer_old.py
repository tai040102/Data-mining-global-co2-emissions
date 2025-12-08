import numpy as np

ES_POP_SIZE = 100
ES_EVAL_LIMIT = 20000
ES_SIGMA_INIT = 5.0
ES_C_INC = 1.2
ES_C_DEC = 0.6

def es_optimize_changes(
        feature_selection,
        fixed_features,
        predict_fn,
        co2_target
):
    np.random.seed(42)

    dims = len(feature_selection)

    lower_bound = []
    upper_bound = []
    feature_names = []

    for item in feature_selection:
        feature_names.append(item["feature"])
        lower_bound.append(item["min_pct"])
        upper_bound.append(item["max_pct"])

    lower_bound = np.array(lower_bound)
    upper_bound = np.array(upper_bound)

    mu = np.zeros(dims)
    mu_fitness = float("inf")

    sigma = ES_SIGMA_INIT
    eval_count = 0

    def indiv_to_dict(indiv):
        return {feature_names[i]: indiv[i] for i in range(dims)}

    # ---------------------------
    # FIXED FITNESS FUNCTION
    # ---------------------------
    def evaluate(indiv):
        f_dict = indiv_to_dict(indiv)
        pred, x = predict_fn(f_dict, fixed_features)

        # Fitness = squared error (chuẩn nhất)
        fitness = (pred - co2_target) ** 2

        return fitness, pred, x

    best_predicted = float("inf")
    best_x = None

    while eval_count < ES_EVAL_LIMIT:
        epsilon = np.random.randn(ES_POP_SIZE, dims)
        offspring = mu + sigma * epsilon

        offspring = np.clip(offspring, lower_bound, upper_bound)

        fitness = []
        preds = []
        xs = []

        for i in range(ES_POP_SIZE):
            fit, pred, x = evaluate(offspring[i])
            fitness.append(fit)
            preds.append(pred)
            xs.append(x)

        fitness = np.array(fitness)
        preds = np.array(preds)
        eval_count += ES_POP_SIZE

        best_idx = np.argmin(fitness)
        best_child = offspring[best_idx]
        best_fit = fitness[best_idx]
        best_pred = preds[best_idx]
        best_child_x = xs[best_idx]

        if best_fit <= mu_fitness:
            mu = best_child.copy()
            mu_fitness = best_fit
            best_predicted = best_pred
            best_x = best_child_x.copy()
            sigma *= ES_C_INC
        else:
            sigma *= ES_C_DEC

        # STOP WHEN GOOD ENOUGH
        if abs(best_predicted - co2_target) < 1e-3:
            break

    best_change = indiv_to_dict(mu)

    return best_change, mu_fitness, best_predicted, best_x

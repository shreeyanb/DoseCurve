from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

# -------------------------------------------------
# LOAD TRAINED MACHINE LEARNING MODEL
# -------------------------------------------------

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "dosecurve_model.pkl"
)

model = joblib.load(MODEL_PATH)

print("DoseCurve ML model loaded successfully!")


# -------------------------------------------------
# CONCENTRATION MODEL
# C(t) = C0 * e^(-ke*t)
# -------------------------------------------------

def concentration(t, c0, ke):
    return c0 * np.exp(-ke * t)


# -------------------------------------------------
# AUC CALCULATION
# -------------------------------------------------

def calculate_auc(c0, ke, total_time=5):
    # Numerical integration using trapezoidal rule
    time = np.linspace(0, total_time, 500)
    conc = concentration(time, c0, ke)

    numerical_auc = np.trapezoid(conc, time)

    # Analytical integral
    analytical_auc = (c0 / ke) * (1 - np.exp(-ke * total_time))

    return numerical_auc, analytical_auc


# -------------------------------------------------
# REPEATED-DOSE MODEL
# -------------------------------------------------

def peak_concentration(dose, vd, ke, tau):
    return (dose / vd) / (1 - np.exp(-ke * tau))


def trough_concentration(dose, vd, ke, tau):
    peak = peak_concentration(dose, vd, ke, tau)
    return peak * np.exp(-ke * tau)


# -------------------------------------------------
# OBJECTIVE FUNCTION
# -------------------------------------------------

def objective(dose, tau, vd, ke):

    target = 5.0
    lambda_reg = 0.0001

    peak = peak_concentration(dose, vd, ke, tau)
    trough = trough_concentration(dose, vd, ke, tau)

    cost = (
        (peak - target) ** 2
        + (trough - target) ** 2
        + lambda_reg * dose ** 2
    )

    return cost


# -------------------------------------------------
# GRADIENT DESCENT
# -------------------------------------------------

def optimize_dose(dose_initial, tau_initial, vd, ke):

    dose = dose_initial
    tau = tau_initial

    # Same scaling approach used in the project
    dose_scale = 300.0
    tau_scale = 1.5

    learning_rate = 0.001

    min_dose = 1e-6
    min_tau = 0.5

    iterations = 100

    history = []

    # Small value used for numerical gradient
    epsilon = 1e-5

    for i in range(iterations):

        # Current objective
        current_cost = objective(dose, tau, vd, ke)

        history.append(current_cost)

        # -----------------------------
        # Numerical gradient wrt dose
        # -----------------------------

        cost_plus_dose = objective(
            dose + epsilon,
            tau,
            vd,
            ke
        )

        cost_minus_dose = objective(
            dose - epsilon,
            tau,
            vd,
            ke
        )

        gradient_dose = (
            cost_plus_dose - cost_minus_dose
        ) / (2 * epsilon)

        # -----------------------------
        # Numerical gradient wrt tau
        # -----------------------------

        cost_plus_tau = objective(
            dose,
            tau + epsilon,
            vd,
            ke
        )

        cost_minus_tau = objective(
            dose,
            tau - epsilon,
            vd,
            ke
        )

        gradient_tau = (
            cost_plus_tau - cost_minus_tau
        ) / (2 * epsilon)

        # -----------------------------
        # Normalize gradients
        # -----------------------------

        normalized_gradient_dose = (
            gradient_dose * dose_scale
        )

        normalized_gradient_tau = (
            gradient_tau * tau_scale
        )

        # -----------------------------
        # Gradient Descent update
        # -----------------------------

        dose = dose - (
            learning_rate *
            normalized_gradient_dose
        )

        tau = tau - (
            learning_rate *
            normalized_gradient_tau
        )

        # Apply constraints
        dose = max(dose, min_dose)
        tau = max(tau, min_tau)

    # Final objective
    final_cost = objective(
        dose,
        tau,
        vd,
        ke
    )

    history.append(final_cost)

    return dose, tau, history


# -------------------------------------------------
# API ROUTE
# -------------------------------------------------

@app.route("/predict", methods=["POST"])
def predict():

    try:

        data = request.get_json()

        # -------------------------------------------------
        # GET INPUT VALUES
        # -------------------------------------------------

        age = float(data["age"])
        weight = float(data["weight"])
        height = float(data["height"])
        sex = int(data["sex"])
        bmi = float(data["bmi"])
        scr = float(data["scr"])
        crcl = float(data["crcl"])
        smoking = int(data["smoking"])
        genotype = data["genotype"]
        albumin = float(data["albumin"])
        alt = float(data["alt"])
        ast = float(data["ast"])
        vd = float(data["vd"])

        # -------------------------------------------------
        # CREATE DATAFRAME FOR ML MODEL
        # -------------------------------------------------

        patient = pd.DataFrame([{
            "age": age,
            "weight": weight,
            "height": height,
            "sex": sex,
            "bmi": bmi,
            "scr": scr,
            "crcl": crcl,
            "smoking": smoking,
            "genotype": genotype,
            "albumin": albumin,
            "alt": alt,
            "ast": ast
        }])

        # -------------------------------------------------
        # ML PREDICTION
        # -------------------------------------------------

        predicted_ke = float(
            model.predict(patient)[0]
        )

        # -------------------------------------------------
        # SINGLE-DOSE CALCULATIONS
        # -------------------------------------------------

        initial_dose = 300.0

        c0 = initial_dose / vd

        numerical_auc, analytical_auc = calculate_auc(
            c0,
            predicted_ke,
            total_time=5
        )

        # -------------------------------------------------
        # GRADIENT DESCENT OPTIMIZATION
        # -------------------------------------------------

        initial_tau = 1.5

        initial_peak = peak_concentration(
            initial_dose,
            vd,
            predicted_ke,
            initial_tau
        )

        initial_trough = trough_concentration(
            initial_dose,
            vd,
            predicted_ke,
            initial_tau
        )

        initial_objective = objective(
            initial_dose,
            initial_tau,
            vd,
            predicted_ke
        )

        optimized_dose, optimized_tau, history = optimize_dose(
            initial_dose,
            initial_tau,
            vd,
            predicted_ke
        )

        optimized_peak = peak_concentration(
            optimized_dose,
            vd,
            predicted_ke,
            optimized_tau
        )

        optimized_trough = trough_concentration(
            optimized_dose,
            vd,
            predicted_ke,
            optimized_tau
        )

        final_objective = objective(
            optimized_dose,
            optimized_tau,
            vd,
            predicted_ke
        )

        # -------------------------------------------------
        # OBJECTIVE REDUCTION
        # -------------------------------------------------

        reduction = (
            (initial_objective - final_objective)
            / initial_objective
        ) * 100

        # -------------------------------------------------
        # CONCENTRATION GRAPH DATA
        # -------------------------------------------------

        time_values = np.linspace(0, 5, 100)

        concentration_values = concentration(
            time_values,
            c0,
            predicted_ke
        )

        # -------------------------------------------------
        # SEND RESULTS TO FRONTEND
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "predicted_ke": predicted_ke,

            "initial_concentration": c0,

            "auc_numerical": numerical_auc,

            "auc_analytical": analytical_auc,

            "initial_dose": initial_dose,

            "initial_interval": initial_tau,

            "initial_peak": initial_peak,

            "initial_trough": initial_trough,

            "initial_objective": initial_objective,

            "optimized_dose": optimized_dose,

            "optimized_interval": optimized_tau,

            "optimized_peak": optimized_peak,

            "optimized_trough": optimized_trough,

            "final_objective": final_objective,

            "objective_reduction": reduction,

            "time": time_values.tolist(),

            "concentration": concentration_values.tolist(),

            "optimization_history": history

        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )

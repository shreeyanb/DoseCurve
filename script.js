document.getElementById("predictButton").addEventListener("click", async function () {

    // Get values from the form
    const age = document.getElementById("age").value;
    const weight = document.getElementById("weight").value;
    const height = document.getElementById("height").value;
    const sex = document.getElementById("sex").value;
    const bmi = document.getElementById("bmi").value;
    const scr = document.getElementById("scr").value;
    const crcl = document.getElementById("crcl").value;
    const smoking = document.getElementById("smoking").value;
    const genotype = document.getElementById("genotype").value;
    const albumin = document.getElementById("albumin").value;
    const alt = document.getElementById("alt").value;
    const ast = document.getElementById("ast").value;
    const vd = document.getElementById("vd").value;

    // Check required fields
    if (
        !age || !weight || !height || !sex || !bmi ||
        !scr || !crcl || !smoking || !genotype ||
        !albumin || !alt || !ast || !vd
    ) {
        alert("Please enter all patient information.");
        return;
    }

    // Disable button while processing
    const button = document.getElementById("predictButton");
    button.disabled = true;
    button.textContent = "Processing...";

    try {

        // Send patient data to Flask backend
        const response = await fetch("http://127.0.0.1:5000/predict", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                age: age,
                weight: weight,
                height: height,
                sex: sex,
                bmi: bmi,
                scr: scr,
                crcl: crcl,
                smoking: smoking,
                genotype: genotype,
                albumin: albumin,
                alt: alt,
                ast: ast,
                vd: vd
            })
        });

        const result = await response.json();

        // Check backend response
        if (!result.success) {
            throw new Error(result.error || "Prediction failed.");
        }

        console.log("Backend response:", result);

        // =========================
        // UPDATE RESULT CARDS
        // =========================

        document.getElementById("ke-result").textContent =
            result.predicted_ke.toFixed(4);

        document.getElementById("auc-result").textContent =
            result.auc_numerical.toFixed(4);

        document.getElementById("dose-result").textContent =
            result.optimized_dose.toFixed(2);

        document.getElementById("interval-result").textContent =
            result.optimized_interval.toFixed(2);


        // =========================
        // UPDATE OPTIMIZATION SUMMARY
        // =========================

        const summary = document.getElementById("optimization-summary");

        if (summary) {
            summary.innerHTML = `
                <strong>Optimization completed successfully.</strong><br><br>

                Predicted elimination rate (kₑ):
                <strong>${result.predicted_ke.toFixed(4)}</strong><br>

                Initial dose:
                <strong>${result.initial_dose.toFixed(2)}</strong><br>

                Optimized simulated dose:
                <strong>${result.optimized_dose.toFixed(2)}</strong><br>

                Optimized dosing interval:
                <strong>${result.optimized_interval.toFixed(2)}</strong><br>

                Initial objective:
                <strong>${result.initial_objective.toFixed(4)}</strong><br>

                Final objective:
                <strong>${result.final_objective.toFixed(4)}</strong><br>

                Objective reduction:
                <strong>${result.objective_reduction.toFixed(2)}%</strong><br><br>

                Peak concentration:
                <strong>${result.optimized_peak.toFixed(4)}</strong><br>

                Trough concentration:
                <strong>${result.optimized_trough.toFixed(4)}</strong>
            `;
        }


        // =========================
        // CONCENTRATION CHART
        // =========================

        if (typeof Chart !== "undefined") {

            const concentrationCanvas =
                document.getElementById("concentrationChart");

            if (concentrationCanvas) {

                // Destroy previous chart if it exists
                if (window.concentrationChart instanceof Chart) {
                    window.concentrationChart.destroy();
                }

                window.concentrationChart = new Chart(
                    concentrationCanvas,
                    {
                        type: "line",

                        data: {
                            labels: result.time,
                          datasets: [{
    label: "Drug Concentration",
    data: result.concentration,
    borderWidth: 2,
    pointRadius: 0,
    fill: false,
    tension: 0.2
}]
                        },

                        options: {
                            responsive: true,

                            scales: {
                            x: {
    title: {
        display: true,
        text: "Time"
    },

    ticks: {
        autoSkip: true,
        maxTicksLimit: 6,

        callback: function(value, index) {
return Number(result.time[index]).toFixed(1);        }
    }
},

                                y: {
                                    title: {
                                        display: true,
                                        text: "Concentration"
                                    }
                                }
                            }
                        }
                    }
                );
            }


            // =========================
            // GRADIENT DESCENT CHART
            // =========================

            const convergenceCanvas =
                document.getElementById("convergenceChart");

            if (convergenceCanvas) {

                if (window.convergenceChart instanceof Chart) {
                    window.convergenceChart.destroy();
                }

                window.convergenceChart = new Chart(
                    convergenceCanvas,
                    {
                        type: "line",

                        data: {
                            labels: result.optimization_history.map(
                                (_, index) => index
                            ),

                            datasets: [{
    label: "Objective Function",
    data: result.optimization_history,
    borderWidth: 2,
    pointRadius: 0,
    fill: false,
    tension: 0.2
}]
                        },

                        options: {
                            responsive: true,

                            scales: {
                                x: {
                                    title: {
                                        display: true,
                                        text: "Iteration"
                                    }
                                },

                                y: {
                                    title: {
                                        display: true,
                                        text: "Objective Value"
                                    }
                                }
                            }
                        }
                    }
                );
            }
        }

        // Scroll to results
        const resultsSection = document.getElementById("results");

        if (resultsSection) {
            resultsSection.scrollIntoView({
                behavior: "smooth"
            });
        }

        alert("Prediction and optimization completed successfully!");

    } catch (error) {

        console.error("Error:", error);

        alert(
            "Could not connect to the DoseCurve backend.\n\n" +
            "Make sure the Flask server is running."
        );

    } finally {

        // Re-enable button
        button.disabled = false;
        button.textContent = "Predict & Optimize";
    }

});
console.log("Health Report System loaded successfully.");


// Show selected file name

const reportFile = document.getElementById("reportFile");
const fileName = document.getElementById("fileName");

if (reportFile) {

    reportFile.addEventListener("change", function () {

        if (reportFile.files.length > 0) {

            fileName.textContent =
                "Selected File: " + reportFile.files[0].name;

        } else {

            fileName.textContent = "";

        }

    });

}


// Analyze Report

function analyzeReport() {

    const file = document.getElementById("reportFile");

    if (!file || file.files.length === 0) {

        alert("Please upload your health report first.");

        return;

    }

    window.location.href = "processing.html";

}


// Processing Page Animation

const processingSteps = document.querySelectorAll(".processing-step");
const progressBar = document.querySelector(".progress-bar");

if (processingSteps.length > 0 && progressBar) {

    let currentStep = 1;

    const processingInterval = setInterval(function () {

        if (currentStep < processingSteps.length) {

            processingSteps[currentStep - 1]
                .classList.remove("active");

            processingSteps[currentStep - 1]
                .classList.add("completed");

            processingSteps[currentStep - 1]
                .querySelector("span")
                .textContent = "✓";

            processingSteps[currentStep]
                .classList.add("active");

            processingSteps[currentStep]
                .querySelector("span")
                .textContent = "⟳";

            progressBar.style.width =
                ((currentStep + 1) * 20) + "%";

            currentStep++;

        } else {

            clearInterval(processingInterval);

            processingSteps[currentStep - 1]
                .classList.remove("active");

            processingSteps[currentStep - 1]
                .classList.add("completed");

            processingSteps[currentStep - 1]
                .querySelector("span")
                .textContent = "✓";

            progressBar.style.width = "100%";

            document.querySelector(".processing-card h1")
                .textContent = "Report Processing Completed";

            document.querySelector(".processing-text")
                .textContent =
                "Your report has been processed successfully. Report analysis page will be added next.";

        }

    }, 2000);

}
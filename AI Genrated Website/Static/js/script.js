/**
 * Core Front-End Logic for Health Report Understanding & Monitoring System
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile Hamburger Menu Toggle
  const mobileToggle = document.getElementById("mobileToggle");
  const navMenu = document.getElementById("navMenu");
  if (mobileToggle && navMenu) {
    mobileToggle.addEventListener("click", function () {
      navMenu.classList.toggle("show");
    });
  }

  // 2. Upload Page Handling (Drag and Drop + File Info Display)
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const fileInfoBox = document.getElementById("fileInfoBox");
  const selectedFileName = document.getElementById("selectedFileName");
  const selectedFileSize = document.getElementById("selectedFileSize");
  const uploadForm = document.getElementById("uploadForm");
  const uploadSubmitBtn = document.getElementById("uploadSubmitBtn");

  if (dropzone && fileInput) {
    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        handleFileSelection(fileInput.files[0]);
      }
    });

    dropzone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
      if (fileInput.files.length > 0) {
        handleFileSelection(fileInput.files[0]);
      }
    });
  }

  function handleFileSelection(file) {
    if (!file) return;
    const allowed = ["pdf", "jpg", "jpeg", "png", "txt"];
    const ext = file.name.split(".").pop().toLowerCase();

    if (!allowed.includes(ext)) {
      alert("Unsupported file format. Please upload PDF, JPG, PNG, or TXT.");
      fileInput.value = "";
      if (fileInfoBox) fileInfoBox.style.display = "none";
      if (uploadSubmitBtn) uploadSubmitBtn.disabled = true;
      return;
    }

    if (file.size > 16 * 1024 * 1024) {
      alert("File size exceeds 16 MB. Please select a smaller file.");
      fileInput.value = "";
      if (fileInfoBox) fileInfoBox.style.display = "none";
      if (uploadSubmitBtn) uploadSubmitBtn.disabled = true;
      return;
    }

    if (selectedFileName) selectedFileName.textContent = file.name;
    if (selectedFileSize) {
      const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
      selectedFileSize.textContent = `${sizeMb} MB`;
    }
    if (fileInfoBox) fileInfoBox.style.display = "flex";
    if (uploadSubmitBtn) uploadSubmitBtn.disabled = false;
  }

  if (uploadForm && uploadSubmitBtn) {
    uploadForm.addEventListener("submit", () => {
      uploadSubmitBtn.disabled = true;
      uploadSubmitBtn.innerHTML = "Uploading Report...";
    });
  }

  // 3. Processing Page Simulation
  const progressFill = document.getElementById("progressFill");
  if (progressFill) {
    runProcessingWorkflow();
  }

  function runProcessingWorkflow() {
    const step1 = document.getElementById("step1");
    const step2 = document.getElementById("step2");
    const step3 = document.getElementById("step3");
    const step4 = document.getElementById("step4");

    progressFill.style.width = "25%";
    setTimeout(() => {
      if (step1) step1.className = "done";
      progressFill.style.width = "50%";
    }, 600);

    setTimeout(() => {
      if (step2) step2.className = "done";
      progressFill.style.width = "75%";
    }, 1200);

    setTimeout(() => {
      if (step3) step3.className = "done";
      progressFill.style.width = "90%";
    }, 1800);

    // Call backend endpoint to trigger parsing logic
    fetch("/api/process-report", { method: "POST" })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          if (step4) step4.className = "done";
          progressFill.style.width = "100%";
          setTimeout(() => {
            window.location.href = "/analysis";
          }, 800);
        } else {
          alert("Error processing report: " + (data.error || "Unknown"));
        }
      })
      .catch((err) => {
        console.error(err);
        // Fallback redirect
        window.location.href = "/analysis";
      });
  }
});

const get = (id) => document.getElementById(id);

const imageInput = get("image-input");
const uploadArea = get("upload-area");
const processButton = get("process-btn");
const downloadButton = get("download-btn");

let selectedFile = null;
let originalWidth = 0;
let originalHeight = 0;
let previewURL = null;
let uploadVersion = 0;
let processedBlob = null;
let processedURL = null;
let processing = false;
let settingsVersion = 0;

const pageOperation = window.location.pathname
    .split("/")
    .pop()
    .replace(/\.html$/, "");

function showStatus(message, isError = false) {
    const status = get("status");
    if (!status) return;
    status.textContent = message;
    status.style.color = isError ? "#dc2626" : "#16803c";
}

function formatFileSize(bytes) {
    if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(1) + " KB";
    }
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function resetResult() {
    if (processedURL) {
        URL.revokeObjectURL(processedURL);
        processedURL = null;
    }

    processedBlob = null;

    const processedImage = get("processed-image");
    if (processedImage) {
        processedImage.hidden = true;
        processedImage.removeAttribute("src");
    }

    const processedInfo = get("processed-info");
    if (processedInfo) {
        processedInfo.textContent = "No processed image yet";
    }

    for (const id of ["conversion-result", "compression-result"]) {
        const result = get(id);
        if (result) result.hidden = true;
    }

    if (downloadButton) downloadButton.disabled = true;
}

function updateResizeUI() {
    const percentageMethod = get("percentage-method");
    if (!percentageMethod) return;

    const usePercentage = percentageMethod.checked;
    get("percentage-settings").hidden = !usePercentage;
    get("custom-settings").hidden = usePercentage;

    const scale = Number(get("scale").value);
    get("scale-value").textContent = scale + "%";

    const originalLabel = get("original-dimensions");
    const resizedLabel = get("resized-dimensions");

    if (!originalWidth || !originalHeight) {
        originalLabel.textContent = "No image uploaded";
        resizedLabel.textContent = "—";
        return;
    }

    originalLabel.textContent =
        `${originalWidth} × ${originalHeight}`;

    let width;
    let height;

    if (usePercentage) {
        width = Math.max(1, Math.round(originalWidth * scale / 100));
        height = Math.max(1, Math.round(originalHeight * scale / 100));
    } else {
        width = Number(get("width").value);
        height = Number(get("height").value);
    }
    
    let error = "";

    if (!usePercentage &&
        (get("width").value.trim() === "" ||
        get("height").value.trim() === "")) {
        error = "Please enter both width and height.";
    } else if (
        !Number.isInteger(width) ||
        !Number.isInteger(height) ||
        width <= 0 ||
        height <= 0
    ) {
        error = "Width and height must be positive whole numbers.";
    } else if (width * height > 20000000) {
        error = "The resized image cannot exceed 20 megapixels.";
    }

    if (error) {
        resizedLabel.textContent = "Invalid dimensions";
        showStatus(error, true);
    } else {
        resizedLabel.textContent = `${width} × ${height}`;
        if (selectedFile) {
            showStatus(
                "Resize settings are valid. Backend not connected yet."
            );
        }
    }
}

function updateFilterUI() {
    const filterSelect = get("filter-type");
    if (!filterSelect) return;

    const type = filterSelect.value;

    get("blur-settings").hidden = type !== "blur";
    get("strength-settings").hidden =
        type !== "sharpen" && type !== "vivid";

    let error = "";

    if (type === "blur") {
        const input = get("blur-radius").value.trim();
        const radius = Number(input);

        if (
            input === "" ||
            !Number.isFinite(radius) ||
            radius < 0 ||
            radius > 20
        ) {
            error = "Blur radius must be between 0 and 20.";
        }
    }

    if (type === "sharpen" || type === "vivid") {
        const input = get("filter-strength").value.trim();
        const strength = Number(input);

        if (
            input === "" ||
            !Number.isFinite(strength) ||
            strength < 0 ||
            strength > 5
        ) {
            error = "Filter strength must be between 0 and 5.";
        }
    }

    if (error) {
        showStatus(error, true);
    } else {
        showStatus(
            selectedFile ? "Filter settings are valid." : ""
        );
    }
}

function updateCropUI() {
    const presetMethod = get("preset-method");
    if (!presetMethod) return;

    get("preset-settings").hidden = !presetMethod.checked;
    get("custom-settings").hidden = presetMethod.checked;

    let error = "";

    if (presetMethod.checked) {
        const ratio = get("crop-ratio").value;

        const validRatios = [
            "1:1", "4:3", "3:2", "16:9", "9:16"
        ];

        if (!validRatios.includes(ratio)) {
            error = "Please select a valid aspect ratio.";
        }

    } else {
        const ids = [
            "crop-left", "crop-top",
            "crop-right", "crop-bottom"
        ];

        const raw = ids.map(id => get(id).value.trim());

        const [left, top, right, bottom] = raw.map(Number);

        if (
            raw.some(value => value === "") ||
            ![left, top, right, bottom].every(Number.isFinite) ||
            !(0 <= left && left < right && right <= 100 &&
              0 <= top && top < bottom && bottom <= 100)
        ) {
            error =
                "Enter valid coordinates: Left < Right, " +
                "Top < Bottom, within 0–100%.";

        } else if (
            originalWidth > 0 &&
            originalHeight > 0 &&
            (
                Math.round(originalWidth * right / 100) <=
                Math.round(originalWidth * left / 100) ||
                Math.round(originalHeight * bottom / 100) <=
                Math.round(originalHeight * top / 100)
            )
        ) {
            error = "Crop region is too small for this image.";
        }
    }

    if (error) {
        showStatus(error, true);
    } else {
        showStatus(
            selectedFile ? "Crop settings are valid." : ""
        );
    }
}

for (const id of [
    "percentage-method", "custom-method",
    "scale", "width", "height"
]) {
    const element = get(id);
    if (element && get("percentage-method")) {
        element.addEventListener("input", updateResizeUI);
        element.addEventListener("change", updateResizeUI);
    }
}

const filterSelect = get("filter-type");
if (filterSelect) {
    filterSelect.addEventListener("change", updateFilterUI);
}

for (const id of ["blur-radius", "filter-strength"]) {
    const element = get(id);
    if (element) {
        element.addEventListener("input", updateFilterUI);
    }
}

for (const id of [
    "preset-method",
    "custom-method",
    "crop-ratio",
    "crop-left",
    "crop-top",
    "crop-right",
    "crop-bottom"
]) {
    const element = get(id);
    if (element) {
        element.addEventListener("input", updateCropUI);
        element.addEventListener("change", updateCropUI);
    }
}


function clearOriginal() {
    if (previewURL) {
        URL.revokeObjectURL(previewURL);
        previewURL = null;
    }

    const originalImage = get("original-image");
    if (originalImage) {
        originalImage.hidden = true;
        originalImage.removeAttribute("src");
    }

    const originalInfo = get("original-info");
    if (originalInfo) {
        originalInfo.textContent = "No image uploaded";
    }

    selectedFile = null;
    originalWidth = 0;
    originalHeight = 0;

    resetResult();
    updateResizeUI();
    updateProcessState();
}

function handleImageUpload(file) {
    if (!file) return;

    const currentVersion = ++uploadVersion;
    clearOriginal();

    const allowedTypes = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ];

    if (!allowedTypes.includes(file.type)) {
        showStatus(
            "Please select a JPG, PNG, or WebP image.",
            true
        );
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showStatus(
            "Image must be no larger than 10 MB.",
            true
        );
        return;
    }

    const url = URL.createObjectURL(file);
    const image = new Image();

    image.onload = () => {
        if (currentVersion !== uploadVersion) {
            URL.revokeObjectURL(url);
            return;
        }

        if (image.naturalWidth * image.naturalHeight > 20000000) {
            URL.revokeObjectURL(url);
            showStatus(
                "Image must be no larger than 20 megapixels.",
                true
            );
            return;
        }

        selectedFile = file;
        originalWidth = image.naturalWidth;
        originalHeight = image.naturalHeight;
        previewURL = url;

        const originalImage = get("original-image");
        if (originalImage) {
            originalImage.src = url;
            originalImage.hidden = false;
        }

        const originalInfo = get("original-info");
        if (originalInfo) {
            originalInfo.textContent =
                `${originalWidth} × ${originalHeight} px | ` +
                formatFileSize(file.size);
        }

        showStatus(`Selected: ${file.name} (${formatFileSize(file.size)})`);
        if (get("filter-type")) {
            updateFilterUI();
        }

        if (get("preset-method")) {
            updateCropUI();
        }
        updateResizeUI();
        updateProcessState();
    };

    image.onerror = () => {
        URL.revokeObjectURL(url);
        if (currentVersion === uploadVersion) {
            showStatus("Unable to open this image.", true);
        }
    };

    image.src = url;
}

if (imageInput) {
    imageInput.addEventListener("change", () => {
        handleImageUpload(imageInput.files[0]);
    });
}

if (uploadArea) {
    uploadArea.addEventListener("dragover", (event) => {
        event.preventDefault();
        uploadArea.classList.add("drag-over");
    });

    uploadArea.addEventListener("dragleave", () => {
        uploadArea.classList.remove("drag-over");
    });

    uploadArea.addEventListener("drop", (event) => {
        event.preventDefault();
        uploadArea.classList.remove("drag-over");

        handleImageUpload(event.dataTransfer.files[0]);
    });
}

if (processButton) processButton.disabled = true;
if (downloadButton) downloadButton.disabled = true;

updateResizeUI();
updateFilterUI();
updateCropUI();

window.addEventListener("beforeunload", () => {
    if (previewURL) URL.revokeObjectURL(previewURL);
});


function updateProcessState() {
    if (!processButton) return;

    let ready = Boolean(
        selectedFile &&
        !processing &&
        window.PixelFaaSAPI
    );

    if (ready) {
        try {
            const params =
                PixelFaaSAPI.buildParams(pageOperation);

            if (
                pageOperation === "resize" &&
                params.get("mode") === "scale"
            ) {
                const factor = Number(params.get("scale"));

                const width = Math.max(
                    1,
                    Math.round(originalWidth * factor)
                );

                const height = Math.max(
                    1,
                    Math.round(originalHeight * factor)
                );

                if (width * height > 20000000) {
                    ready = false;
                }
            }

            if (
                pageOperation === "crop" &&
                params.get("mode") === "custom"
            ) {
                const l = Number(params.get("left"));
                const t = Number(params.get("top"));
                const r = Number(params.get("right"));
                const b = Number(params.get("bottom"));

                const leftPx =
                    Math.round(originalWidth * l / 100);
                const rightPx =
                    Math.round(originalWidth * r / 100);
                const topPx =
                    Math.round(originalHeight * t / 100);
                const bottomPx =
                    Math.round(originalHeight * b / 100);

                if (
                    rightPx <= leftPx ||
                    bottomPx <= topPx
                ) {
                    ready = false;
                }
            }
        } catch (error) {
            ready = false;
        }
    }

    processButton.disabled = !ready;
}

const parameterIds = [
    "percentage-method",
    "custom-method",
    "scale",
    "width",
    "height",
    "filter-type",
    "blur-radius",
    "filter-strength",
    "preset-method",
    "crop-ratio",
    "crop-left",
    "crop-top",
    "crop-right",
    "crop-bottom",
    "output-format"
];

for (const id of parameterIds) {
    const element = get(id);

    if (!element) continue;

    const changed = () => {
        settingsVersion++;
        resetResult();
        updateProcessState();
    };

    element.addEventListener("input", changed);
    element.addEventListener("change", changed);
}

if (processButton) {
    processButton.addEventListener("click", async () => {
        if (!selectedFile || processing) return;

        const file = selectedFile;
        const currentUpload = uploadVersion;
        const currentSettings = settingsVersion;

        processing = true;

        resetResult();
        updateProcessState();
        showStatus("Processing image...");

        try {
            const blob =
                await PixelFaaSAPI.processImage(
                    pageOperation,
                    file
                );

            if (
                currentUpload !== uploadVersion ||
                currentSettings !== settingsVersion ||
                file !== selectedFile
            ) {
                return;
            }

            processedBlob = blob;
            processedURL = URL.createObjectURL(blob);

            const processedImage = get("processed-image");

            if (processedImage) {
                processedImage.src = processedURL;
                processedImage.hidden = false;
            }

            const processedInfo = get("processed-info");

            if (processedInfo) {
                processedInfo.textContent =
                    "Processed image | " +
                    formatFileSize(blob.size);
            }

            const conversionResult =
                get("conversion-result");

            if (conversionResult) {
                conversionResult.hidden = false;

                get("converted-file-info").textContent =
                    blob.type
                        .replace("image/", "")
                        .toUpperCase() +
                    " | " +
                    formatFileSize(blob.size);
            }

            const compressionResult =
                get("compression-result");

            if (compressionResult) {
                compressionResult.hidden = false;

                get("original-size").textContent =
                    formatFileSize(file.size);

                get("compressed-size").textContent =
                    formatFileSize(blob.size);

                const change =
                    (1 - blob.size / file.size) * 100;

                get("compression-ratio").textContent =
                    change >= 0
                        ? `Reduced by ${change.toFixed(1)}%`
                        : `Output is ${(-change).toFixed(1)}% larger than the original`;
            }

            if (downloadButton) {
                downloadButton.disabled = false;
            }

            showStatus("Image processed successfully.");

        } catch (error) {
            if (
                currentUpload === uploadVersion &&
                currentSettings === settingsVersion &&
                file === selectedFile
            ) {
                showStatus(
                    error.message || "Image processing failed.",
                    true
                );
            }

        } finally {
            processing = false;
            updateProcessState();
        }
    });
}

if (downloadButton) {
    downloadButton.addEventListener("click", () => {
        if (!processedBlob || !selectedFile) return;

        PixelFaaSAPI.downloadImage(
            processedBlob,
            pageOperation,
            selectedFile.name
        );
    });
}

window.addEventListener("beforeunload", () => {
    if (processedURL) {
        URL.revokeObjectURL(processedURL);
    }
});

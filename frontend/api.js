window.PixelFaaSAPI = (() => {
    const endpoints = {
        resize: "",
        watermark: "",
        convert: "",
        compress: "",
        filter: "",
        crop: ""
    };

    function value(id) {
        const element = document.getElementById(id);

        if (!element) {
            throw new Error(`Missing input: ${id}`);
        }

        return element.value.trim();
    }

    function numberValue(id, min, max, wholeNumber = false) {
        const raw = value(id);
        const number = Number(raw);

        if (
            raw === "" ||
            !Number.isFinite(number) ||
            number < min ||
            number > max ||
            (wholeNumber && !Number.isInteger(number))
        ) {
            throw new Error(
                `Please enter a valid value for ${id}.`
            );
        }

        return number;
    }

    function buildParams(operation) {
        const params = new URLSearchParams();

        switch (operation) {
            case "resize":
                if (
                    document.getElementById(
                        "percentage-method"
                    ).checked
                ) {
                    params.set("mode", "scale");
                    params.set(
                        "scale",
                        String(numberValue("scale", 10, 200) / 100)
                    );
                } else {
                    const width = numberValue(
                        "width", 1, 20000000, true
                    );

                    const height = numberValue(
                        "height", 1, 20000000, true
                    );

                    if (width * height > 20000000) {
                        throw new Error(
                            "The output cannot exceed 20 megapixels."
                        );
                    }

                    params.set("mode", "dimensions");
                    params.set("width", String(width));
                    params.set("height", String(height));
                }
                break;

            case "watermark":
                params.set("text", "PixelFaaS");
                params.set("position", "bottom-right");
                params.set("opacity", "60");
                break;

            case "convert":
                params.set("format", value("output-format"));
                break;

            case "compress":
                params.set("quality", "80");
                break;

            case "filter": {
                const type = value("filter-type");

                params.set("filter", type);

                if (type === "blur") {
                    params.set(
                        "radius",
                        String(numberValue("blur-radius", 0, 20))
                    );
                }

                if (type === "sharpen" || type === "vivid") {
                    params.set(
                        "strength",
                        String(numberValue("filter-strength", 0, 5))
                    );
                }
                break;
            }

            case "crop":
                if (
                    document.getElementById(
                        "preset-method"
                    ).checked
                ) {
                    params.set("mode", "preset");
                    params.set(
                        "ratio",
                        value("crop-ratio")
                    );
                } else {
                    const left = numberValue(
                        "crop-left", 0, 100
                    );

                    const top = numberValue(
                        "crop-top", 0, 100
                    );

                    const right = numberValue(
                        "crop-right", 0, 100
                    );

                    const bottom = numberValue(
                        "crop-bottom", 0, 100
                    );

                    if (left >= right || top >= bottom) {
                        throw new Error(
                            "Crop coordinates must satisfy " +
                            "Left < Right and Top < Bottom."
                        );
                    }

                    params.set("mode", "custom");
                    params.set("left", String(left));
                    params.set("top", String(top));
                    params.set("right", String(right));
                    params.set("bottom", String(bottom));
                }
                break;

            default:
                throw new Error(
                    `Unknown operation: ${operation}`
                );
        }

        return params;
    }

    async function processImage(operation, file) {
        const endpoint = endpoints[operation];

        if (!endpoint) {
            throw new Error(
                `OpenFaaS endpoint for ${operation} ` +
                "is not configured yet."
            );
        }

        if (!(file instanceof Blob)) {
            throw new Error(
                "Please upload an image first."
            );
        }

        const url = new URL(
            endpoint,
            window.location.href
        );

        for (const [key, val] of buildParams(operation)) {
            url.searchParams.set(key, val);
        }

        const response = await fetch(url.toString(), {
            method: "POST",
            headers: {
                "Content-Type":
                    file.type || "application/octet-stream"
            },
            body: file
        });

        if (!response.ok) {
            let message =
                `OpenFaaS request failed ` +
                `(HTTP ${response.status}).`;

            try {
                const data = await response.json();

                if (typeof data.error === "string") {
                    message = data.error;
                }
            } catch (_) {
            }

            throw new Error(message);
        }

        const result = await response.blob();

        if (
            !result.size ||
            ![
                "image/jpeg",
                "image/png",
                "image/webp"
            ].includes(result.type)
        ) {
            throw new Error(
                "The backend did not return a supported image."
            );
        }

        return result;
    }

    function downloadImage(
        blob,
        operation,
        originalName = "image"
    ) {
        const extensions = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp"
        };

        const extension = extensions[blob.type];

        if (!extension) {
            throw new Error(
                "Unsupported download format."
            );
        }

        const basename = originalName.replace(
            /\.[^.]+$/,
            ""
        );

        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;
        link.download =
            `${basename}-${operation}.${extension}`;

        document.body.appendChild(link);

        link.click();
        link.remove();

        setTimeout(() => {
            URL.revokeObjectURL(url);
        }, 1000);
    }

    return {
        buildParams,
        processImage,
        downloadImage
    };
})();

document.addEventListener("DOMContentLoaded", function () {
    initializeFormControls();
    initializeDynamicFormsets();
    initializeMasterCodePicker();
    initializeWorkforceVisibility();
});

function initializeFormControls(scope = document) {
    scope.querySelectorAll("input, select, textarea").forEach(function (field) {
        if (field.type === "checkbox" || field.type === "radio" || field.type === "file") return;

        if (!field.classList.contains("form-control") && !field.classList.contains("form-select")) {
            if (field.tagName.toLowerCase() === "select") {
                field.classList.add("form-select");
            } else {
                field.classList.add("form-control");
            }
        }
    });
}

function initializeDynamicFormsets() {
    document.addEventListener("click", function (event) {
        const button = event.target.closest("[data-formset-add]");
        if (!button) return;

        event.preventDefault();

        const sectionKey = button.getAttribute("data-formset-add");
        addFormsetRow(sectionKey);
    });
}

function addFormsetRow(sectionKey) {
    const container = document.querySelector(`[data-formset-container="${sectionKey}"]`);
    if (!container) return;

    const rows = Array.from(container.querySelectorAll("[data-formset-row]"));
    if (!rows.length) return;

    const currentRow = rows[rows.length - 1];
    const formPrefix = detectFormPrefix(currentRow);
    if (!formPrefix) return;

    const totalFormsInput = document.querySelector(`input[name="${formPrefix}-TOTAL_FORMS"]`);
    if (!totalFormsInput) return;

    const newIndex = parseInt(totalFormsInput.value, 10);
    const newRow = currentRow.cloneNode(true);

    updateIndexes(newRow, formPrefix, newIndex);
    clearNewRow(newRow);

    container.appendChild(newRow);
    totalFormsInput.value = newIndex + 1;

    initializeFormControls(newRow);

    if (sectionKey === "workforce") {
        setTimeout(function () {
            initializeWorkforceVisibility();
        }, 50);
    }
}

function detectFormPrefix(row) {
    const field = row.querySelector("input[name], select[name], textarea[name]");
    if (!field || !field.name) return null;

    const match = field.name.match(/^(.+)-\d+-/);
    return match ? match[1] : null;
}

function updateIndexes(row, formPrefix, newIndex) {
    const regex = new RegExp(`${escapeRegExp(formPrefix)}-(\\d+)-`, "g");

    row.querySelectorAll("*").forEach(function (element) {
        ["name", "id", "for"].forEach(function (attr) {
            if (!element.hasAttribute(attr)) return;

            const oldValue = element.getAttribute(attr);
            const newValue = oldValue.replace(regex, `${formPrefix}-${newIndex}-`);
            element.setAttribute(attr, newValue);
        });
    });
}

function clearNewRow(row) {
    row.querySelectorAll("input, select, textarea").forEach(function (field) {
        if (field.type === "hidden" && field.name && field.name.endsWith("-id")) {
            field.value = "";
            return;
        }

        if (field.type === "file") {
            field.value = "";
            return;
        }

        if (field.hasAttribute("data-selected-code-display")) {
            field.value = "";
            return;
        }

        if (field.type === "checkbox" || field.type === "radio") {
            field.checked = false;
            return;
        }

        if (field.classList.contains("workforce-labor-type-ui")) {
            field.value = "rd_worker";
            return;
        }

        if (field.tagName.toLowerCase() === "select") {
            field.selectedIndex = 0;
            return;
        }

        field.value = "";
    });
}

function initializeMasterCodePicker() {
    let activeRow = null;
    let selectedCode = null;

    document.addEventListener("click", function (event) {
        const openButton = event.target.closest("[data-open-master-code-modal]");
        if (openButton) {
            activeRow = openButton.closest("[data-formset-row]");
            selectedCode = null;
            renderMasterCodeResults();
        }

        const resultButton = event.target.closest("[data-master-code-result]");
        if (resultButton) {
            selectedCode = {
                id: resultButton.dataset.id,
                code: resultButton.dataset.code,
                description: resultButton.dataset.description || ""
            };

            document.getElementById("generatedCodePreview").textContent = selectedCode.code;
            document.getElementById("useGeneratedCodeButton").disabled = false;
        }

        const useButton = event.target.closest("#useGeneratedCodeButton");
        if (useButton && activeRow && selectedCode) {
            const hiddenSelect = activeRow.querySelector("select[name$='-master_code']");
            const displayInput = activeRow.querySelector("[data-selected-code-display]");
            const descriptionField = activeRow.querySelector("[name$='-description']");

            if (hiddenSelect) {
                hiddenSelect.value = selectedCode.id;
                hiddenSelect.dispatchEvent(new Event("change", { bubbles: true }));
            }

            if (displayInput) {
                displayInput.value = selectedCode.code;
            }

            if (descriptionField && !descriptionField.value) {
                descriptionField.value = selectedCode.description;
            }

            activeRow = null;
            selectedCode = null;
        }
    });

    const searchInput = document.getElementById("masterCodeSearchInput");
    const phaseSelect = document.getElementById("modalProjectPhase");
    const categorySelect = document.getElementById("modalCategory");
    const subcategorySelect = document.getElementById("modalSubcategory");

    [searchInput, phaseSelect, categorySelect, subcategorySelect].forEach(function (field) {
        if (field) {
            field.addEventListener("input", renderMasterCodeResults);
            field.addEventListener("change", renderMasterCodeResults);
        }
    });
}

function renderMasterCodeResults() {
    const resultsBox = document.getElementById("masterCodeResults");
    if (!resultsBox) return;

    const searchValue = (document.getElementById("masterCodeSearchInput")?.value || "").toLowerCase();
    const phaseValue = document.getElementById("modalProjectPhase")?.value || "";
    const categoryValue = document.getElementById("modalCategory")?.value || "";
    const subcategoryValue = document.getElementById("modalSubcategory")?.value || "";

    const allCodes = Array.from(document.querySelectorAll("[data-master-code]"));

    resultsBox.innerHTML = "";

    const filteredCodes = allCodes.filter(function (item) {
        const text = (
            item.dataset.code + " " +
            item.dataset.description + " " +
            item.dataset.phaseName + " " +
            item.dataset.categoryName + " " +
            item.dataset.subcategoryName
        ).toLowerCase();

        if (searchValue && !text.includes(searchValue)) return false;
        if (phaseValue && item.dataset.phase !== phaseValue) return false;
        if (categoryValue && item.dataset.category !== categoryValue) return false;
        if (subcategoryValue && item.dataset.subcategory !== subcategoryValue) return false;

        return true;
    });

    filteredCodes.slice(0, 50).forEach(function (item) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-light text-start border";
        button.setAttribute("data-master-code-result", "true");
        button.dataset.id = item.dataset.id;
        button.dataset.code = item.dataset.code;
        button.dataset.description = item.dataset.description || "";

        button.innerHTML = `
            <strong>${item.dataset.code}</strong>
            <div class="small text-muted">${item.dataset.description || ""}</div>
        `;

        resultsBox.appendChild(button);
    });

    if (!filteredCodes.length) {
        resultsBox.innerHTML = `<div class="alert alert-warning mb-0">No matching master codes found.</div>`;
    }

    const preview = document.getElementById("generatedCodePreview");
    const useButton = document.getElementById("useGeneratedCodeButton");

    if (preview) preview.textContent = "No code selected";
    if (useButton) useButton.disabled = true;
}

/* WORKFORCE LOGIC */
document.addEventListener("change", function (event) {
    if (event.target.matches(".workforce-labor-type-ui")) {
        const row = event.target.closest("[data-formset-row]");
        updateWorkforceRowVisibility(row);
    }
});

function initializeWorkforceVisibility() {
    document.querySelectorAll("[data-formset-container='workforce'] [data-formset-row]").forEach(function (row) {
        initializeWorkforceLaborTypeValue(row);
        updateWorkforceRowVisibility(row);
    });
}

function initializeWorkforceLaborTypeValue(row) {
    if (!row) return;

    const laborTypeUi = row.querySelector(".workforce-labor-type-ui");
    const entryType = row.querySelector("select[name$='-entry_type']");
    const externalType = row.querySelector("select[name$='-external_source_type']");

    if (!laborTypeUi || !entryType) return;

    if (entryType.value === "rd_worker") {
        laborTypeUi.value = "rd_worker";
    } else if (entryType.value === "external" && externalType && externalType.value === "rental") {
        laborTypeUi.value = "rental";
    } else if (entryType.value === "external" && externalType && externalType.value === "subcontractor") {
        laborTypeUi.value = "subcontractor";
    } else {
        laborTypeUi.value = "rd_worker";
    }
}

function updateWorkforceRowVisibility(row) {
    if (!row) return;

    const laborTypeUi = row.querySelector(".workforce-labor-type-ui");
    const entryType = row.querySelector("select[name$='-entry_type']");
    const externalType = row.querySelector("select[name$='-external_source_type']");

    if (!laborTypeUi || !entryType) return;

    const laborValue = laborTypeUi.value;

    if (laborValue === "rd_worker") {
        entryType.value = "rd_worker";
        if (externalType) externalType.value = "";
    }

    if (laborValue === "rental") {
        entryType.value = "external";
        if (externalType) externalType.value = "rental";
    }

    if (laborValue === "subcontractor") {
        entryType.value = "external";
        if (externalType) externalType.value = "subcontractor";
    }

    const isRD = laborValue === "rd_worker";
    const isRental = laborValue === "rental";
    const isSubcontractor = laborValue === "subcontractor";

    toggleBoxes(row, ".workforce-rd-box", isRD);
    toggleBoxes(row, ".workforce-rental-box", isRental);
    toggleBoxes(row, ".workforce-source-box", isRental || isSubcontractor);
    toggleBoxes(row, ".workforce-subcontractor-box", isSubcontractor);
    toggleBoxes(row, ".workforce-time-box", isRD || isRental);
}

function toggleBoxes(row, selector, show) {
    row.querySelectorAll(selector).forEach(function (box) {
        box.style.display = show ? "" : "none";

        box.querySelectorAll("input, select, textarea").forEach(function (field) {
            if (field.type === "file") return;

            if (show) {
                field.removeAttribute("disabled");
            } else {
                field.setAttribute("disabled", "disabled");
            }
        });
    });
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

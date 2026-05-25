document.addEventListener("DOMContentLoaded", function () {
    initializeFormControls();
    initializeDynamicFormsets();
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
    if (!container) {
        console.error("Missing formset container:", sectionKey);
        return;
    }

    const activeRows = Array.from(container.querySelectorAll("[data-formset-row]"))
        .filter(row => row.style.display !== "none");

    if (!activeRows.length) {
        console.error("No active row found:", sectionKey);
        return;
    }

    const currentRow = activeRows[activeRows.length - 1];
    const formPrefix = detectFormPrefix(currentRow);

    if (!formPrefix) {
        console.error("Cannot detect form prefix:", sectionKey);
        return;
    }

    const totalFormsInput = document.querySelector(`input[name="${formPrefix}-TOTAL_FORMS"]`);

    if (!totalFormsInput) {
        console.error("TOTAL_FORMS not found:", formPrefix);
        return;
    }

    const newIndex = parseInt(totalFormsInput.value, 10);

    const newRow = currentRow.cloneNode(true);

    const historyCard = buildHistoryCard(currentRow, sectionKey);

    container.insertBefore(historyCard, currentRow);

    currentRow.style.display = "none";

    updateIndexes(newRow, formPrefix, newIndex);
    clearNewRow(newRow);

    container.appendChild(newRow);
    totalFormsInput.value = newIndex + 1;

    initializeFormControls(newRow);

    newRow.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });
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
    row.style.display = "";

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

        if (field.tagName.toLowerCase() === "select") {
            field.selectedIndex = 0;
            return;
        }

        field.value = "";
    });
}

function buildHistoryCard(row, sectionKey) {
    const card = document.createElement("div");
    card.className = "history-summary mb-3";

    getSummaryValues(row, sectionKey).forEach(function (item) {
        const cell = document.createElement("div");
        cell.className = "history-cell";
        cell.innerHTML = `
            <span>${item.label}</span>
            <strong>${item.value || "-"}</strong>
        `;
        card.appendChild(cell);
    });

    return card;
}

function getSummaryValues(row, sectionKey) {
    function getValue(selector) {
        const field = row.querySelector(selector);
        if (!field) return "";

        if (field.hasAttribute("data-selected-code-display")) {
            return field.value || "";
        }

        if (field.tagName.toLowerCase() === "select") {
            return field.options[field.selectedIndex]?.text || "";
        }

        return field.value || "";
    }

    if (sectionKey === "work") {
        return [
            { label: "Code", value: getValue("[data-selected-code-display]") },
            { label: "Description", value: getValue("[name$='-description']") },
            { label: "Floor", value: getValue("[name$='-project_area']") },
            { label: "Qty", value: getValue("[name$='-quantity']") }
        ];
    }

    if (sectionKey === "blocked") {
        return [
            { label: "Code", value: getValue("[data-selected-code-display]") },
            { label: "Issue", value: getValue("[name$='-issue']") },
            { label: "Reason", value: getValue("[name$='-reason']") }
        ];
    }

    if (sectionKey === "visits") {
        return [
            { label: "Visitor", value: getValue("[name$='-visitor_name']") },
            { label: "Entity", value: getValue("[name$='-visitor_entity']") },
            { label: "Time", value: getValue("[name$='-visit_time']") }
        ];
    }

    if (sectionKey === "workforce") {
        return [
            { label: "Worker", value: getValue("[name$='-worker_name']") },
            { label: "Source", value: getValue("[name$='-worker_source']") },
            { label: "Hours", value: getValue("[name$='-normal_hours']") },
            { label: "OT", value: getValue("[name$='-overtime_hours']") }
        ];
    }

    if (sectionKey === "equipment") {
        return [
            { label: "Equipment", value: getValue("[name$='-equipment']") },
            { label: "Qty", value: getValue("[name$='-quantity']") },
            { label: "Working", value: getValue("[name$='-working_hours']") }
        ];
    }

    if (sectionKey === "materials") {
        return [
            { label: "Material", value: getValue("[name$='-material_name']") },
            { label: "Qty", value: getValue("[name$='-quantity']") },
            { label: "Supplier", value: getValue("[name$='-supplier']") }
        ];
    }

    return [{ label: "Entry", value: "Added" }];
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
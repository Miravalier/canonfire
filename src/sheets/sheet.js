import { AddCharacterUpdate } from "./pending_updates.js";
import { ApiRequest } from "./requests.js";

export class Sheet {
    constructor(id, window) {
        this.id = id;
        this.window = window;
        this.cachedData = {};
        this.inputs = [];
    }

    registerBatchedInput(selector, key) {
        /** @type {HTMLInputElement} */
        const element = this.window.content.querySelector(selector);
        if (!element) {
            console.error(`Can't find "${selector}" in character sheet`);
            return null;
        }
        element.addEventListener("input", async () => {
            const update = { id: this.id };
            update[key] = element.value;
            AddCharacterUpdate(update);
        });
        this.inputs.push([key, element]);
        return element;
    }

    registerInput(selector, key) {
        /** @type {HTMLInputElement} */
        const element = this.window.content.querySelector(selector);
        if (!element) {
            console.error(`Can't find "${selector}" in character sheet`);
            return null;
        }
        element.addEventListener("input", async () => {
            const update = { id: this.id };
            update[key] = element.value;
            await ApiRequest("/character/update", update);
        });
        this.inputs.push([key, element]);
        return element;
    }

    addListeners() {
    }

    update(data) {
        if (data.name !== this.cachedData.name) {
            this.window.titleNode.textContent = data.name;
        }
        for (const [key, element] of this.inputs) {
            if (data[key] !== this.cachedData[key]) {
                element.value = data[key];
            }
        }
    }
}

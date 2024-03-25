import { state } from "../state.js";

/**
 * UI Element containing:
 * - "model" setting
 * - "temperature" setting
 * - "max_tokens" setting
 * - "no_rag" setting
 * - "no_history" setting
 *
 * Automatically populates:
 * - `state.model` (on change)
 * - `state.temperature` (on change)
 * - `state.max_tokens` (on key up)
 */
export class SettingsDialog extends HTMLElement {
  connectedCallback() {
    // Enforce singleton pattern: there can only be 1 instance of this element in the DOM
    for (const node of [...document.querySelectorAll("chat-flow")].slice(1)) {
      node.remove();
    }

    this.renderInnerHTML();

    // Event listener for "model" select
    this.querySelector("#model").addEventListener("change", (e) => {
      if (state.availableModels.includes(e.target.value)) {
        state.model = e.target.value;
      }
    });

    // Event listener for "temperature" select
    this.querySelector("#temperature").addEventListener("change", (e) => {
      const temperature = parseFloat(e.target.value) * 10;

      if (temperature < 0 || temperature > 20) {
        return;
      }

      state.temperature = (temperature / 10).toFixed(1);
    });

    // Event listener for "max_tokens"
    this.querySelector("#max_tokens").addEventListener("keyup", (e) => {
      state.maxTokens = parseInt(e.target.value);
    });

    // Event listener for "search_toggle" select
    this.querySelector("#search_toggle").addEventListener("change", (e) => {
      state.searchEnabled = e.target.value === "enabled";
    });

    // Event listener for "history_toggle" select
    this.querySelector("#history_toggle").addEventListener("change", (e) => {
      state.historyEnabled = e.target.value === "enabled";
    });

    // Event listener for "close"
    this.querySelector(".close").addEventListener("click", this.close);
  }

  /**
   * Opens underlying `<dialog>`
   * @returns {void}
   */
  open = () => {
    this.querySelector("dialog").showModal();
  };

  /**
   * Closes underlying `<dialog>`
   * @returns {void}
   */
  close = () => {
    this.querySelector("dialog").close();
  };

  renderInnerHTML = () => {
    let modelSelectOptions = /*html*/ ``;
    let temperatureSelectOptions = /*html*/ ``;

    for (const model of state.availableModels) {
      modelSelectOptions += /*html*/ `
      <option 
        value="${model}" 
        ${model == state.defaultModel ? "selected" : ""}>
        ${model}
      </option>
      `;
    }

    for (let i = 0; i < 21; i++) {
      const temperature = (i / 10).toFixed(1);
      temperatureSelectOptions += /*html*/ `<option value="${temperature}">${temperature}</option>`;
    }

    this.innerHTML = /*html*/ `
    <dialog>
      <button class="close">Close</button>
      <h2>Settings</h2>

      <form>
        <label for="model">Model</label>
        <select id="model" name="model">
          ${modelSelectOptions}
        </select>

        <label for="temperature">Temperature</label>
        <select id="temperature" name="temperature">
          ${temperatureSelectOptions}
        </select>

        <label for="search_toggle">Search</label>
        <select id="search_toggle" name="search_toggle">
          <option value="enabled" ${state.searchEnabled ? 'selected' : ''}>Enabled</option>
          <option value="disabled">Disabled</option>
        </select>

        <label for="history_toggle">History</label>
        <select id="history_toggle" name="history_toggle">
          <option value="enabled" ${state.historyEnabled ? 'selected' : ''}>Enabled</option>
          <option value="disabled">Disabled</option>
        </select>

        <label for="max_tokens">Max tokens</label>
        <input type="number" name="max_tokens" id="max_tokens" value="" placeholder="Default">
      </form>
    </dialog>
    `;
  };
}
customElements.define("settings-dialog", SettingsDialog);

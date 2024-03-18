import { state } from "../state.js";

/**
 * UI Element containing:
 * - Main text input (message)
 * - "Ask" button
 * - "Stop" button
 * - "Settings" button
 * - "Inspect" button
 *
 * Automatically populates:
 * - `state.message` (on key up)
 *
 * Automatically enables / disables relevant inputs based on app state.
 */
export class ChatInput extends HTMLElement {
  /** Holds reference to interval function calling `this.stateCheck` */
  stateCheckInterval = null;

  /** Reference to `form > textarea` */
  inputTextAreaRef = null;

  /** Reference to `form > .actions > button[data-action="stop"]` */
  stopButtonRef = null;

  /** Reference to `form > .actions > button[data-action="ask"] */
  askButtonRef = null;

  connectedCallback() {
    // Enforce singleton
    for (const node of [...document.querySelectorAll("chat-flow")].slice(1)) {
      node.remove();
    }

    this.renderInnerHTML();

    // Grab shared element references
    this.inputTextAreaRef = this.querySelector("textarea");
    this.stopButtonRef = this.querySelector(`button[data-action="stop"]`);
    this.askButtonRef = this.querySelector(`button[data-action="ask"]`);

    // Event listeners for Settings / Inspect dialogs
    for (const dialogName of ["settings", "inspect"]) {
      const button = this.querySelector(
        `button[data-action="open-${dialogName}"]`
      );

      button.addEventListener("click", (e) => {
        e.preventDefault();
        document.querySelector(`${dialogName}-dialog`).open();
      });
    }

    // Event listener for submit ("Ask")
    this.querySelector("form").addEventListener("submit", (e) => {
      e.preventDefault();
      document.querySelector("chat-flow").ask();
    });

    // Event listener for "Stop"
    this.stopButtonRef.addEventListener("click", (e) => {
      e.preventDefault();
      document.querySelector("chat-flow").stopStreaming();
    });

    // Event listener to capture text input (message)
    this.inputTextAreaRef.addEventListener("keyup", (e) => {
      e.preventDefault();
      state.message = this.inputTextAreaRef.value.trim();
    });

    // Check every 100ms what parts of this component need to be disabled
    this.stateCheckInterval = setInterval(this.stateCheck, 100);
  }

  disconnectedCallback() {
    clearInterval(this.stateCheckInterval);
  }

  /**
   * Determines what parts of this component need to be disabled based on app state.
   * To be called periodically.
   * @returns {void}
   */
  stateCheck = () => {
    // Input textarea: disabled while processing
    if (state.processing) {
      this.inputTextAreaRef.setAttribute("disabled", "disabled");
      this.inputTextAreaRef.value = "Please wait ...";
    } else {
      this.inputTextAreaRef.removeAttribute("disabled");
    }

    // "Ask" button is enabled when:
    // - A message was provided
    // - A model was picked
    // - A temperature was picked
    // - App is not processing / streaming
    if (
      !state.processing &&
      !state.streaming &&
      state.model &&
      state.temperature != null &&
      state.message
    ) {
      this.askButtonRef.removeAttribute("disabled");
    } else {
      this.askButtonRef.setAttribute("disabled", "disabled");
    }

    // "Stop" button: enabled while streaming
    if (state.streaming) {
      this.stopButtonRef.removeAttribute("disabled");
    } else {
      this.stopButtonRef.setAttribute("disabled", "disabled");
    }
  };

  renderInnerHTML = () => {
    this.innerHTML = /*html*/ `
    <form>
      <textarea 
        id="message" 
        placeholder="This chatbot can answer questions about web archive files it ingested." 
        required></textarea>
      
      <div class="actions">
        <button class="hollow" data-action="open-settings">Settings</button>
        <button class="hollow" data-action="open-inspect">Inspect</button>
        <button class="hollow" data-action="stop" disabled>Stop</button>
        <button class="ask" data-action="ask"disabled>Ask</button>
      </div>
    </form>
    `;
  };
}
customElements.define("chat-input", ChatInput);

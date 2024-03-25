import { state } from "../state.js";

/**
 * UI Element representing a chat bubble.
 *
 * Available values for "type" attribute:
 * - "user": User message
 * - "ai": Message from AI.
 * - "error": Standard error message.
 * - "analyzing-request": System message letting the user know that the system is analyzing the request.
 * - "confirm-search": Interactive message asking the user to confirm before performing a RAG search.
 * - "sources": Message listing sources (state.searchResults)
 *
 * Uses app state + type to determine what contents to render.
 */
export class ChatBubble extends HTMLElement {
  connectedCallback() {
    const type = this.getAttribute("type");

    switch (type) {
      case "user":
        this.renderUserBubble();
        break;

      case "ai":
        this.renderAIBubble();
        break;

      case "sources":
        this.renderSourcesBubble();
        break;

      case "error":
      default:
        this.renderErrorBubble();
        break;
    }
  }

  /**
   * Renders a "user" bubble.
   * Uses the current value of `state.message`.
   * @returns {void}
   */
  renderUserBubble = () => {
    this.innerHTML = /*html*/ `
    <p class="text">${this.sanitizeString(state.message)}</p>
    `;
  };

  /**
   * Renders an "ai" bubble.
   * Text starts empty and is later streamed from `<chat-flow>`.
   * @returns {void}
   */
  renderAIBubble = () => {
    this.innerHTML = /*html*/ `
    <p class="actor">${this.sanitizeString(state.model)}</p>
    <p class="text"></p>
    `;
  };

  /**
   * Renders an "sources" bubble listing everything under state.searchResults.
   * @returns {void}
   */
  renderSourcesBubble = () => {
    let sourcesHTML = "";

    for (let i in state.searchResults ) {

      const source = state.searchResults[i];
      const filename = this.sanitizeString(source.warc_filename, false);
      const uri = this.sanitizeString(source.warc_record_target_uri, false);
      const date = this.sanitizeString(source.warc_record_date, false);
      const recordId = this.sanitizeString(source.warc_record_id, false);
      const text = this.sanitizeString(source.warc_record_text, false);

      sourcesHTML += /*html*/`
      <details>
        <summary>[${parseInt(i)+1}] ${filename}</summary>

        <table>
          <tr>
            <td>URL: </td>
            <td>
              <a href="${uri}">${uri}</a>
            </td>
          </tr>

          <tr>
            <td>Date: </td>
            <td><span>${date}</span></td>
          </tr>

          <tr>
            <td>Record ID: </td>
            <td><span>${recordId}</span></td>
          </tr>
        </table>

        <textarea disabled>${text}</textarea>
      </details>
      `;
    }

    this.innerHTML = /*html*/`<p class="actor">Sources</p>${sourcesHTML}`;
  };

  /**
   * Renders an "error" bubble.
   * @returns {void}
   */
  renderErrorBubble = () => {
    this.innerHTML = /*html*/ `
    <p class="text">An error occurred (see console for details), please try again.</p>
    `;
  };

  /**
   * Escapes <, > and converts line breaks into <br>.
   * @param {string} string
   * @param {boolean} convertLineBreaks
   * @returns {void}
   */
  sanitizeString = (string, convertLineBreaks = true) => {
    string = string.trim().replaceAll("<", "&lt;").replaceAll(">", "&gt;");

    if (convertLineBreaks === true) {
      string = string.replaceAll("\n", "<br>");
    }

    return string;
  };
}
customElements.define("chat-bubble", ChatBubble);

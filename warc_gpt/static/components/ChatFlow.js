import { state } from "../state.js";

/**
 * UI Element containing:
 * - List of chat "bubbles" from the user, AI and system.
 *
 * Handles the processing of requests via its `ask()` and `streamCompletion()` methods.
 *
 * Automatically populates:
 * - `state.processing`
 * - `state.history`
 * - `state.searchStatement`
 * - `state.searchTarget`
 * - `state.searchResults`
 *
 * Automatically enables / disables relevant inputs based on app state.
 */
export class ChatFlow extends HTMLElement {
  /** Reference to the paragraph with the last "ai" bubble in which text should be streamed. */
  currentAICursorRef = null;

  connectedCallback() {
    // Enforce singleton
    for (const node of [...document.querySelectorAll("chat-flow")].slice(1)) {
      node.remove();
    }

    this.renderInnerHTML();
  }

  /**
   * Processes a request from user (main entry point)
   * @returns {Promise<void>}
   */
  ask = async () => {
    // Remove placeholder if still present
    this.querySelector(".placeholder")?.remove();

    // Compile payload
    const searchEnabled = state.searchEnabled;
    const message = state.message;
    const model = state.model;
    const temperature = state.temperature;

    if (!message || !model || temperature === null) {
      this.addBubble("error");
      this.end();
      return;
    }

    // Block UI
    state.processing = true;

    // Inject user message
    this.addBubble("user");
    state.log(state.message, "User sent a message");

    // Perform search
    if (searchEnabled === true) {
      try {
        const response = await fetch("/api/search", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ message }),
        });

        const data = await response.json();

        if (data.length < 1) {
          throw new Error("/api/search returned no results.")
        }

        state.searchResults = data;
        this.addBubble("sources");
        state.log(JSON.stringify(state.searchResults, null, 2), "/api/search");

      } catch (err) {
        console.error(err);
        this.addBubble("error");

        state.log(
          "Could not perform search against collection.",
          "/api/search"
        );
        
        this.end();
        return;
      }
    }

    // Start completion
    this.streamCompletion();
  };

  /**
   * Stops streaming.
   * @returns {void}
   */
  stopStreaming = () => {
    state.log("Streaming interrupted by user.");
    state.streaming = false;
  };

  /**
   * Ends System/AI turn, goes back to user for input.
   * @returns {void}
   */
  end = () => {
    state.processing = false;
    document.querySelector("chat-input textarea").value = "";
  };

  /**
   * Inserts a chat bubble of a given type at the end of `chat-flow`.
   * @param {string} type
   * @returns {void}
   */
  addBubble = (type) => {
    const bubble = document.createElement("chat-bubble");
    bubble.setAttribute("type", type);

    this.insertAdjacentElement("beforeend", bubble);

    if (type === "ai") {
      this.currentAICursorRef = bubble.querySelector(".text");
    }

    this.scrollIntoConversation();
  };


  /**
   * Sends completion request to API and streams results into the last <chat-bubble type="ai"> of the list.
   * Payload is determined by app state.
   * @returns {Promise<void>}
   */
  streamCompletion = async () => {
    let output = "";
    let response = null;
    let responseStream = null;
    const decoder = new TextDecoder();

    //
    // Compile payload
    //
    const message = state.message;
    const model = state.model;
    const temperature = state.temperature;
    const maxTokens = state.maxTokens;
    const searchResults = state.searchResults;
    const history = state.historyEnabled === true ? state.history : [];

    if (!message || !model || temperature === null) {
      this.addBubble("error");
      return;
    }

    //
    // Start completion request
    //
    try {
      response = await fetch("/api/complete", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message,
          model,
          temperature,
          max_tokens: maxTokens,
          history,
          search_results: searchResults,
        }),
      });

      if (response.status != 200) {
        throw new Error((await response.json())?.error);
      }
    } catch (err) {
      this.addBubble("error");
      console.error(err);
      this.end();
      return;
    }

    //
    // Stream text into "ai" bubble as it comes
    //
    try {
      state.streaming = true;
      responseStream = response.body.getReader();

      // Inject "ai" bubble to stream into
      this.addBubble("ai");

      // Stream
      while (true) {
        const { done, value } = await responseStream.read();

        const textChunk = decoder.decode(value, { stream: true });
        this.pushAITextChunk(textChunk);
        output += textChunk;

        if (done || !state.streaming) {
          break;
        }
      }

      // Log and add interaction to history
      state.log(output, "/api/complete");
      state.history.push({ role: "user", content: state.message });
      state.history.push({ role: "assistant", content: output });
    } finally {
      // Clear state of that interaction
      state.searchResults = [];
      state.message = "";

      state.streaming = false;
      this.end();
    }
  };

  /**
   * Pushes a chunk of text into last <chat-bubble type="ai"> of the list.
   * @param {string} chunk
   * @returns {void}
   */
  pushAITextChunk = (chunk) => {
    // Strip common markdown markers
    // [!] Temporary - should be replaced by proper markdown strip or interpreter.
    chunk = chunk.replace("**", "");
    chunk = chunk.replace("##", "");
    chunk = chunk.replace("###", "");

    const cursor = this.currentAICursorRef;
    cursor.textContent = cursor.textContent + chunk;

    this.scrollIntoConversation();
  };

  /**
   * Automatically scroll to the bottom of the conversation.
   */
  scrollIntoConversation = () => {
    this.scroll({
      top: this.scrollHeight,
      left: 0,
      behavior: "smooth",
    });
  };

  renderInnerHTML = () => {
    this.innerHTML = /*html*/ `
      <img class="placeholder" 
            src="/static/images/logo-title-color.svg"
            aria-hidden="true"
            alt="" />
    `;
  };
}
customElements.define("chat-flow", ChatFlow);

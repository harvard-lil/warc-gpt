const constants = window.WARC_GPT_CONST;

/**
 * @typedef {object} WARCGPTState - App-wide "state". All components are assumed to be able to read and write from this object.
 * @property {boolean} processing - If `true`, the app is considered "busy". Used to control UI state.
 * @property {boolean} streaming - If `true`, the app is currently streaming content. Used to control UI state.
 * @property {Array} searchResults - Latest output from `/api/search`.
 * @property {?string} message - Latest message typed by the user.
 * @property {?string} model - Latest model picked by the user.
 * @property {?Number} maxTokens - Latest value picked by the user for "max tokens".
 * @property {?boolean} searchEnabled - Lates value picked by the use for "search_toggle"
 * @property {?boolean} historyEnabled - Lates value picked by the use for "history_toggle"
 * @property {{role: string, content: string}[]} history - Keeps track of "basic" chat history. To be fed back to the API with each exchange.
 * @property {?function} log - Shortcut for InspectDialog.log(text, title).
 * @property {string} basePrompt - Transcript of the base prompt.
 * @property {string} historyPrompt - Transcript of the history part of the prompt.
 * @property {string} ragPrompt - Transcript of the RAG (context) part of the prompt.
 * @property {string[]} availableModels - List of models that can be used.
 * @property {string} defaultModel - Model to be used by default.
 * @property {string} reducedMotion - Whether the `prefers-reduced-motion: reduce` directive was detected.
 */

/**
 * Basic "state" object used across the app to share data.
 * @type {WARCGPTState}
 */
export const state = {
  processing: false,
  streaming: false,
  searchResults: [],
  message: null,
  model: constants.default_model,
  temperature: 0.0,
  maxTokens: null,
  searchEnabled: true,
  historyEnabled: true,
  history: [],

  log: () => {},

  basePrompt: constants.text_completion_base_prompt,
  historyPrompt: constants.text_completion_history_prompt,
  ragPrompt: constants.text_completion_rag_prompt,
  availableModels: constants.available_models,
  defaultModel: constants.default_model,

  reducedMotion: window.matchMedia(`(prefers-reduced-motion: reduce)`) === true || window.matchMedia(`(prefers-reduced-motion: reduce)`).matches === true
};

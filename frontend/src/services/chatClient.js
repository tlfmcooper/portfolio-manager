/** Gemini-compatible conversation adapter backed by the authenticated API. */
async function* readEvents(body) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let pending = '';
  let dataLines = [];
  try {
    while (true) {
      const { value, done } = await reader.read();
      pending += done ? decoder.decode() : decoder.decode(value, { stream: true });
      let newline;
      while ((newline = pending.indexOf('\n')) !== -1) {
        const line = pending.slice(0, newline).replace(/\r$/, '');
        pending = pending.slice(newline + 1);
        if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
        else if (!line && dataLines.length) {
          const data = JSON.parse(dataLines.join('\n'));
          dataLines = [];
          yield data;
        }
      }
      if (done) break;
    }
  } finally {
    try { await reader.cancel(); } finally { reader.releaseLock(); }
  }
}

const makeResponse = (parts) => ({
  text: () => parts.filter(part => !part.thought).map(part => part.text || '').join(''),
  functionCalls: () => parts.filter(part => part.functionCall).map(part => part.functionCall),
});

export function chatErrorMessage(error) {
  if (error.response?.status === 409) return 'Save your Gemini API key in chat settings to continue.';
  if (error.response?.status === 400) return 'Gemini rejected the request. Check your saved API key and the configured model.';
  if (error.response?.status === 429) return 'Gemini quota or rate limit reached. Please try again later.';
  if (error.response?.status === 401) return 'Please log in again to continue.';
  if (error.response?.status === 503) return 'Chat secret storage is unavailable. Please try again later.';
  return 'Chat is unavailable or the response was interrupted. Please try again.';
}

export function createChatClient(api, { systemInstruction, tools, signal }) {
  return {
    startChat({ history = [] } = {}) {
      let contents = [...history];
      const chat = {
        async sendMessageStream(parts) {
          signal?.throwIfAborted();
          const nextContents = [...contents, { role: 'user', parts }];
          // The fetch adapter preserves the shared JWT injection/refresh interceptors.
          // Axios only retries a rejected HTTP response, never a started stream.
          const result = await api.post('/chat/generate', {
            contents: nextContents,
            systemInstruction: { parts: [{ text: systemInstruction }] },
            tools,
          }, { adapter: 'fetch', responseType: 'stream', signal,
            headers: { Accept: 'text/event-stream' } });
          let resolveResponse;
          let rejectResponse;
          const response = new Promise((resolve, reject) => {
            resolveResponse = resolve;
            rejectResponse = reject;
          });
          // A failed stream can throw before the caller awaits the aggregate response.
          response.catch(() => {});
          const stream = (async function* () {
            const modelParts = [];
            let completed = false;
            try {
              for await (const chunk of readEvents(result.data)) {
                signal?.throwIfAborted();
                if (chunk.error) throw new Error('Chat response interrupted.');
                if (chunk.done) { completed = true; break; }
                if (chunk.promptFeedback?.blockReason) throw new Error('Chat response blocked.');
                const candidate = chunk.candidates?.[0];
                if (candidate?.finishReason && !['STOP', 'MAX_TOKENS'].includes(candidate.finishReason)) {
                  throw new Error('Chat response could not be completed.');
                }
                const chunkParts = candidate?.content?.parts || [];
                modelParts.push(...chunkParts);
                yield makeResponse(chunkParts);
              }
              if (!completed) throw new Error('Chat response interrupted.');
              contents = [...nextContents, { role: 'model', parts: modelParts }];
              resolveResponse(makeResponse(modelParts));
            } catch (error) {
              rejectResponse(error);
              throw error;
            }
          })();
          return { stream, response };
        },
        async sendMessage(parts) {
          const result = await chat.sendMessageStream(parts);
          for await (const chunk of result.stream) { void chunk; }
          return { response: await result.response };
        },
      };
      return chat;
    },
  };
}

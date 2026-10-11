import { describe, expect, it, vi } from 'vitest';
import { createChatClient } from '../../src/services/chatClient';
import { resolveAgentTools } from '../../src/tools/agentConversation';

function stream(events, { done = true } = {}) {
  const text = events.map(event => `data: ${JSON.stringify(event)}\r\n\r\n`).join('') + (done ? 'data: {"done":true}\r\n\r\n' : '');
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({ start(controller) {
    // Split at arbitrary byte boundaries, including inside UTF-8 characters.
    for (let i = 0; i < bytes.length; i += 3) controller.enqueue(bytes.slice(i, i + 3));
    controller.close();
  } });
}
const candidate = parts => ({ candidates: [{ content: { parts } }] });
const options = { systemInstruction: 'Helpful', tools: [{ functionDeclarations: [] }] };

describe('backend chat conversation adapter', () => {
  it('streams text, preserves screenshot input, and never sends an API key', async () => {
    const api = { post: vi.fn().mockResolvedValue({ data: stream([candidate([{ text: 'Hello é' }])]) }) };
    const chat = createChatClient(api, options).startChat();
    const input = [{ text: 'Hi' }, { inlineData: { mimeType: 'image/jpeg', data: 'base64' } }];
    const result = await chat.sendMessageStream(input);
    let text = '';
    for await (const chunk of result.stream) text += chunk.text();
    expect(text).toBe('Hello é');
    expect((await result.response).text()).toBe('Hello é');
    expect(api.post.mock.calls[0][1].contents[0].parts).toEqual(input);
    expect(api.post.mock.calls[0][2]).toMatchObject({ adapter: 'fetch', responseType: 'stream', headers: { Accept: 'text/event-stream' } });
    expect(JSON.stringify(api.post.mock.calls)).not.toContain('api_key');
  });

  it('preserves call IDs and thought signatures over multiple tool rounds', async () => {
    const part = { functionCall: { name: 'first', args: {}, id: 'id-1' }, thoughtSignature: 'signature' };
    const api = { post: vi.fn()
      .mockResolvedValueOnce({ data: stream([candidate([part])]) })
      .mockResolvedValueOnce({ data: stream([candidate([{ functionCall: { name: 'second', args: {} } }])]) })
      .mockResolvedValueOnce({ data: stream([candidate([{ text: 'Final result' }])]) }) };
    const chat = createChatClient(api, options).startChat();
    const initial = await chat.sendMessage([{ text: 'Analyze' }]);
    const execute = vi.fn().mockResolvedValue('{"value":42}');
    const result = await resolveAgentTools(chat, initial.response, execute);
    expect(result.response.text()).toBe('Final result');
    expect(result.results).toHaveLength(2);
    const contents = api.post.mock.calls[1][1].contents;
    expect(contents[1].parts).toEqual([part]);
    expect(contents[2].parts[0].functionResponse).toEqual({ name: 'first', id: 'id-1', response: { value: 42 } });
  });

  it.each([
    [stream([{ error: 'Interrupted' }]), 'interrupted'],
    [stream([candidate([{ text: 'partial' }])], { done: false }), 'interrupted'],
    [stream([{ promptFeedback: { blockReason: 'SAFETY' } }]), 'blocked'],
  ])('rejects failed or truncated streams without replay', async (body, message) => {
    const api = { post: vi.fn().mockResolvedValue({ data: body }) };
    const chat = createChatClient(api, options).startChat();
    await expect(chat.sendMessage([{ text: 'Hi' }])).rejects.toThrow(message);
    expect(api.post).toHaveBeenCalledTimes(1);
  });

  it('does not make a request after cancellation', async () => {
    const controller = new AbortController();
    controller.abort();
    const api = { post: vi.fn() };
    const chat = createChatClient(api, { ...options, signal: controller.signal }).startChat();
    await expect(chat.sendMessage([{ text: 'Hi' }])).rejects.toThrow();
    expect(api.post).not.toHaveBeenCalled();
  });
});

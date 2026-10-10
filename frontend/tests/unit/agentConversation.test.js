import { expect, it, vi } from 'vitest';
import { resolveAgentTools } from '../../src/tools/agentConversation';

it('supports context then preview tool rounds and sends structured function responses', async () => {
  const final = { functionCalls: () => [], text: () => 'Here is your proposal.' };
  const preview = { functionCalls: () => [{ name: 'preview_allocation_scenario', args: { preset: 'msr' } }] };
  const chat = { sendMessage: vi.fn().mockResolvedValueOnce({ response: preview }).mockResolvedValueOnce({ response: final }) };
  const execute = vi.fn().mockResolvedValueOnce('{"AAA":80,"CASH":20}').mockResolvedValueOnce('{"ui_type":"allocation_scenario"}');
  const result = await resolveAgentTools(chat, { functionCalls: () => [{ name: 'get_analytics_weight_context', id: 'call-1', args: {} }] }, execute);
  expect(chat.sendMessage).toHaveBeenNthCalledWith(1, [{ functionResponse: { name: 'get_analytics_weight_context', id: 'call-1', response: { AAA: 80, CASH: 20 } } }]);
  expect(result.results).toHaveLength(2);
  expect(result.response.text()).toBe('Here is your proposal.');
  expect(result.limitReached).toBe(false);
});

it('bounds repeated tool calls and wraps plain tool messages', async () => {
  const response = { functionCalls: () => [{ name: 'reset_analytics' }] };
  const chat = { sendMessage: vi.fn().mockResolvedValue({ response }) };
  const result = await resolveAgentTools(chat, response, async () => 'Reset complete.', 2);
  expect(chat.sendMessage).toHaveBeenCalledTimes(2);
  expect(chat.sendMessage).toHaveBeenCalledWith([{ functionResponse: { name: 'reset_analytics', response: { message: 'Reset complete.' } } }]);
  expect(result.limitReached).toBe(true);
});

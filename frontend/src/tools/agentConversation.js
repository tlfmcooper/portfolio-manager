/** Complete tool rounds using the Gemini function-response protocol. */
export async function resolveAgentTools(chat, initialResponse, execute, maxRounds = 4) {
  let response = initialResponse;
  const results = [];
  for (let round = 0; round < maxRounds; round++) {
    const calls = response.functionCalls?.() || [];
    if (!calls.length) return { response, results, limitReached: false };
    const parts = [];
    for (const call of calls) {
      const result = await execute(call.name, call.args || {});
      results.push({ name: call.name, args: call.args || {}, result });
      let output;
      try { output = JSON.parse(result); } catch { output = { message: result }; }
      if (!output || typeof output !== 'object' || Array.isArray(output)) output = { result: output };
      parts.push({ functionResponse: { name: call.name, response: output, ...(call.id ? { id: call.id } : {}) } });
    }
    response = (await chat.sendMessage(parts)).response;
  }
  return { response, results, limitReached: !!response.functionCalls?.()?.length };
}

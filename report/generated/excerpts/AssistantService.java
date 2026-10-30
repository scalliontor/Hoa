public class AssistantService {
    // ... (other members omitted)
    /** Tool-calling loop: ask Gemma, run the tools it chooses, give it the results, at most three rounds. */
    public AssistantReply ask(String customerId, String message) {
        List<String> toolsUsed = new ArrayList<>();
        List<Map<String, Object>> messages = new ArrayList<>();
        messages.add(Map.of("role", "system", "content", SYSTEM));
        messages.add(Map.of("role", "user", "content", message));
        try {
            for (int round = 0; round < 3; round++) {
                LlmReply reply = llmClient.chat(messages, tools());
                if (!reply.hasToolCalls()) return new AssistantReply(reply.getContent(), toolsUsed, true);
                messages.add(assistantTurn(reply));
                for (ToolCall call : reply.getToolCalls()) {
                    toolsUsed.add(call.getName());
                    messages.add(Map.of("role", "tool", "tool_call_id", call.getId(),
                            "content", runTool(customerId, call)));
                }
            }
            return new AssistantReply("Sorry, I could not finish that request. Please ask again.", toolsUsed, true);
        } catch (RuntimeException e) {
            return answerWithoutAi(customerId, message);
        }
    }

    /** The four tools Gemma may call, in the OpenAI "tools" format. */
    private List<Map<String, Object>> tools() {
        return List.of(
                tool("search_paintings", "Search the catalogue with a natural-language request, e.g. "
                        + "'blue landscape paintings' or 'Monet paintings under 100 dollars'.", "query", "The request"),
                tool("find_order", "Look up one order of the signed-in customer by its number.",
                        "order_id", "The order number, e.g. 20261001"),
                tool("latest_order", "Get the newest order of the signed-in customer.", null, null),
                tool("list_orders", "List all orders of the signed-in customer.", null, null));
    }
}

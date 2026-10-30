package com.ptit.ecom.application.service;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.ptit.ecom.application.search.SearchResult;
import com.ptit.ecom.application.search.SearchService;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderItem;
import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.infrastructure.ai.LlmClient;
import com.ptit.ecom.infrastructure.ai.LlmReply;
import com.ptit.ecom.infrastructure.ai.ToolCall;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Shopping assistant: Gemma 4 picks a tool, the service runs it (Chapter 3).
 * The customer id always comes from the session, never from the model, so Gemma cannot read other orders (NFR01).
 */
public class AssistantService {
    private static final Gson GSON = new Gson();
    private static final String SYSTEM = "You are the curator assistant of Họa., an online shop selling museum-quality "
            + "prints of public-domain paintings and frames. Answer in English in at most three short sentences. "
            + "Always use the tools to look up paintings and orders and never invent order numbers, prices or "
            + "states. The customer is already signed in, so you never need a customer id. Prices are in US dollars.";
    private static final Pattern ORDER_NUMBER = Pattern.compile("\\b(\\d{8,14})\\b");
    private LlmClient llmClient;
    private SearchService searchService;
    private OrderService orderService;

    public AssistantService(LlmClient llmClient, SearchService searchService, OrderService orderService) {
        this.llmClient = llmClient;
        this.searchService = searchService;
        this.orderService = orderService;
    }

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

    /** Runs a tool for the session customer and returns its result as JSON text for Gemma. */
    private String runTool(String customerId, ToolCall call) {
        JsonObject arguments = call.getArguments() == null || call.getArguments().isBlank()
                ? new JsonObject() : JsonParser.parseString(call.getArguments()).getAsJsonObject();
        try {
            switch (call.getName()) {
                case "search_paintings":
                    return GSON.toJson(paintingSummaries(searchService.searchText(arguments.get("query").getAsString())));
                case "find_order":
                    return GSON.toJson(orderSummary(orderService.getOrder(customerId,
                            arguments.get("order_id").getAsString())));
                case "latest_order":
                    Order latest = orderService.latestOrder(customerId);
                    return latest == null ? "{\"error\": \"You have no orders yet\"}" : GSON.toJson(orderSummary(latest));
                case "list_orders":
                    List<Map<String, Object>> orders = new ArrayList<>();
                    for (Order order : orderService.listOrders(customerId)) orders.add(orderSummary(order));
                    return GSON.toJson(orders);
                default:
                    return "{\"error\": \"Unknown tool\"}";
            }
        } catch (RuntimeException e) {
            return GSON.toJson(Map.of("error", String.valueOf(e.getMessage())));
        }
    }

    /** Without Gemma (NFR02): an order number, "latest" or "orders" pick the tool, anything else is a search. */
    private AssistantReply answerWithoutAi(String customerId, String message) {
        String text = message.toLowerCase();
        Matcher number = ORDER_NUMBER.matcher(text);
        try {
            if (number.find()) {
                return offline(describe(orderService.getOrder(customerId, number.group(1))), "find_order");
            }
            if (text.contains("latest") || text.contains("last order") || text.contains("recent")) {
                Order latest = orderService.latestOrder(customerId);
                return offline(latest == null ? "You have no orders yet." : describe(latest), "latest_order");
            }
            if (text.contains("order")) {
                List<String> orders = new ArrayList<>();
                for (Order order : orderService.listOrders(customerId)) {
                    orders.add(order.getOrderId() + " (" + order.getStatus().name().toLowerCase() + ")");
                }
                return offline(orders.isEmpty() ? "You have no orders yet."
                        : "You have " + orders.size() + " orders: " + String.join(", ", orders) + ".", "list_orders");
            }
            List<SearchResult> results = searchService.searchText(message);
            if (results.isEmpty()) return offline("I found no paintings for that request.", "search_paintings");
            StringBuilder answer = new StringBuilder("You may like: ");
            for (SearchResult result : results.subList(0, Math.min(3, results.size()))) {
                answer.append(result.getProduct().getName()).append(" ($")
                        .append(result.getProduct().getPrice().stripTrailingZeros().toPlainString()).append("); ");
            }
            return offline(answer.toString().replaceAll("; $", "."), "search_paintings");
        } catch (RuntimeException e) {
            return offline(e.getMessage(), "find_order");
        }
    }

    private static AssistantReply offline(String answer, String tool) {
        return new AssistantReply("(Gemma 4 is offline) " + answer, List.of(tool), false);
    }

    private static String describe(Order order) {
        String text = "order " + order.getOrderId() + " is " + order.getStatus().name().toLowerCase()
                + ", total $" + order.getTotalAmount().stripTrailingZeros().toPlainString();
        if (order.getShipping() != null && order.getShipping().getTrackingNumber() != null) {
            text += ", tracking " + order.getShipping().getCarrier() + " " + order.getShipping().getTrackingNumber();
        }
        return text.substring(0, 1).toUpperCase() + text.substring(1) + ".";
    }

    private static List<Map<String, Object>> paintingSummaries(List<SearchResult> results) {
        List<Map<String, Object>> summaries = new ArrayList<>();
        for (SearchResult result : results.subList(0, Math.min(5, results.size()))) {
            Map<String, Object> summary = new LinkedHashMap<>();
            summary.put("product_id", result.getProduct().getProductId());
            summary.put("name", result.getProduct().getName());
            if (result.getProduct() instanceof Painting) {
                summary.put("artist", ((Painting) result.getProduct()).getArtist().getName());
            }
            summary.put("price_usd", result.getProduct().getPrice());
            summary.put("why", result.getReason());
            summaries.add(summary);
        }
        return summaries;
    }

    private static Map<String, Object> orderSummary(Order order) {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("order_id", order.getOrderId());
        summary.put("order_status", order.getStatus().name());
        summary.put("date", order.getOrderDate().toString());
        summary.put("total_usd", order.getTotalAmount());
        List<String> items = new ArrayList<>();
        for (OrderItem item : order.getItems()) items.add(item.getQuantity() + " x " + item.getProduct().getName());
        summary.put("items", items);
        if (order.getShipping() != null) {
            summary.put("carrier", order.getShipping().getCarrier());
            summary.put("tracking_number", order.getShipping().getTrackingNumber());
            summary.put("delivery_status", order.getShipping().getStatus().name());
            summary.put("address", order.getShipping().getAddress().format());
        }
        return summary;
    }

    private static Map<String, Object> assistantTurn(LlmReply reply) {
        List<Map<String, Object>> calls = new ArrayList<>();
        for (ToolCall call : reply.getToolCalls()) {
            calls.add(Map.of("id", call.getId(), "type", "function",
                    "function", Map.of("name", call.getName(), "arguments", call.getArguments())));
        }
        Map<String, Object> turn = new LinkedHashMap<>();
        turn.put("role", "assistant");
        turn.put("content", reply.getContent() == null ? "" : reply.getContent());
        turn.put("tool_calls", calls);
        return turn;
    }

    private static Map<String, Object> tool(String name, String description, String parameter, String parameterText) {
        Map<String, Object> properties = new LinkedHashMap<>();
        if (parameter != null) properties.put(parameter, Map.of("type", "string", "description", parameterText));
        Map<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("type", "object");
        parameters.put("properties", properties);
        parameters.put("required", parameter == null ? List.of() : List.of(parameter));
        return Map.of("type", "function",
                "function", Map.of("name", name, "description", description, "parameters", parameters));
    }
}

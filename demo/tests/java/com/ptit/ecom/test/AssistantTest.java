package com.ptit.ecom.test;

import static com.ptit.ecom.test.Fixtures.freshDatabase;
import static com.ptit.ecom.test.Fixtures.searchService;
import static com.ptit.ecom.test.TestRunner.check;
import static com.ptit.ecom.test.TestRunner.same;
import static com.ptit.ecom.test.TestRunner.test;

import com.ptit.ecom.application.service.AssistantReply;
import com.ptit.ecom.application.service.AssistantService;
import com.ptit.ecom.application.service.OrderService;
import com.ptit.ecom.infrastructure.repository.sqlite.Database;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteOrderRepository;
import com.ptit.ecom.test.Fixtures.FakeLlmClient;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** AssistantService: Gemma 4 chooses a tool, the service runs it for the signed-in customer only. */
final class AssistantTest {
    private AssistantTest() {
    }

    static void run() {
        test("Gemma is offered exactly four tools, none with a customer id parameter", () -> {
            FakeLlmClient gemma = FakeLlmClient.online().answer("Hello!");
            assistant(gemma).ask("C001", "hello");
            List<String> names = new ArrayList<>();
            for (Map<String, Object> tool : gemma.toolLists.get(0)) {
                Map<?, ?> function = (Map<?, ?>) tool.get("function");
                names.add((String) function.get("name"));
                Map<?, ?> properties = (Map<?, ?>) ((Map<?, ?>) function.get("parameters")).get("properties");
                check(!properties.containsKey("customer_id") && !properties.containsKey("customerId"),
                        "tool " + function.get("name") + " takes no customer id");
            }
            same(List.of("search_paintings", "find_order", "latest_order", "list_orders"), names, "tools");
        });
        test("find my order 20261001: Gemma calls find_order and answers from the tool result", () -> {
            FakeLlmClient gemma = FakeLlmClient.online().callTool("find_order", "{\"order_id\": \"20261001\"}")
                    .answer("Your order 20261001 has shipped with GHN Express, tracking GHN26102001.");
            AssistantReply reply = assistant(gemma).ask("C001", "find my order 20261001");
            same(List.of("find_order"), reply.getToolsUsed(), "tools used");
            check(reply.getAiUsed() && reply.getAnswer().contains("GHN26102001"), "answer " + reply.getAnswer());
            String toolResult = toolMessage(gemma);
            check(toolResult.contains("SHIPPED") && toolResult.contains("GHN26102001"), "tool result " + toolResult);
        });
        test("A tool call for another customer's order returns only 'not found' to Gemma (NFR01)", () -> {
            FakeLlmClient gemma = FakeLlmClient.online().callTool("find_order", "{\"order_id\": \"20261003\"}")
                    .answer("I could not find that order in your account.");
            assistant(gemma).ask("C001", "find my order 20261003");
            String toolResult = toolMessage(gemma);
            check(toolResult.contains("not found"), "tool result " + toolResult);
            check(!toolResult.contains("Tran") && !toolResult.contains("172") && !toolResult.contains("A003"),
                    "nothing about the other customer's order: " + toolResult);
        });
        test("Offline (NFR02): rules answer 'where is my latest order?'", () -> {
            AssistantReply reply = assistant(FakeLlmClient.offline()).ask("C001", "where is my latest order?");
            check(reply.getAnswer().startsWith("(Gemma 4 is offline)"), "prefix: " + reply.getAnswer());
            check(reply.getAnswer().contains("20261001"), "latest order of C001: " + reply.getAnswer());
            same(List.of("latest_order"), reply.getToolsUsed(), "tool");
            check(!reply.getAiUsed(), "AI not used");
        });
        test("Offline: an order number of another customer is refused, a request is searched", () -> {
            AssistantService assistant = assistant(FakeLlmClient.offline());
            check(assistant.ask("C001", "find my order 20261003").getAnswer().contains("was not found"), "refusal");
            String list = assistant.ask("C001", "list my orders").getAnswer();
            check(list.contains("20261001 (shipped)") && list.contains("20261002 (delivered)"), "list " + list);
            AssistantReply search = assistant.ask("C001", "Monet paintings under 100 dollars");
            check(search.getAnswer().contains("Impression, Sunrise"), "search answer " + search.getAnswer());
        });
    }

    private static AssistantService assistant(FakeLlmClient gemma) throws Exception {
        Database database = freshDatabase();
        return new AssistantService(gemma, searchService(database, FakeLlmClient.offline()),
                new OrderService(new SqliteOrderRepository(database)));
    }

    /** The content of the tool message sent back to Gemma in the second round. */
    private static String toolMessage(FakeLlmClient gemma) {
        for (Map<String, Object> message : gemma.conversations.get(1)) {
            if ("tool".equals(message.get("role"))) return (String) message.get("content");
        }
        throw new AssertionError("no tool message was sent to Gemma");
    }
}

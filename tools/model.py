"""Single source of truth for the essay (Chapters 1-4) and the demo application.

Requirements and use cases (Chapters 1-2), the analysis model (4.1), the data
model and tables (4.2), the design classes (4.3), the layers (4.4) and the
generated Java code (4.5) are all read from this file, so the VP diagrams, the
SQL, the Java code and the report cannot drift apart.

Member strings use UML notation: "-name: Type" for attributes and
"+name(p: T, q: U): R {static|abstract}" for operations; an operation whose
name equals its class is a constructor.
"""
import re

BASE_PACKAGE = "com.ptit.ecom"

# ------------------------------------------------- Chapter 1: requirements
# (id, kind, title, use case ids). Demo queries come from the A06 problem statement.
REQUIREMENTS = [
    ("FR01", "FR", "Search paintings by keyword or natural sentence, filtered by style, subject, colour, artist and maximum price", ["UC02"]),
    ("FR02", "FR", "Search by voice: self-hosted Whisper turns speech into text, the customer edits it and searches as text", ["UC03"]),
    ("FR03", "FR", "Search by image: Gemma 4 describes the photo (style, subject, colour), it is encoded as a vector and matched by cosine similarity", ["UC04"]),
    ("FR04", "FR", "Multimodal search combining text and image with weighted scores", ["UC01"]),
    ("FR05", "FR", "View painting details: artist, year, size, medium, price, stock; add a frame", ["UC05"]),
    ("FR06", "FR", "Manage the cart: add, change quantity, remove a line", ["UC06"]),
    ("FR07", "FR", "Checkout: create an order from the cart, freeze prices, decrease stock, empty the cart", ["UC07"]),
    ("FR08", "FR", "View my orders and my latest order", ["UC08"]),
    ("FR09", "FR", "Look up an order by id; only orders of the signed-in customer are returned", ["UC09"]),
    ("FR10", "FR", "AI shopping assistant: Gemma 4 understands the question and calls tools to search paintings and look up orders", ["UC10"]),
    ("NFR01", "NFR", "Security: the customer id comes from the session and order ownership is checked on the server", ["UC08", "UC09", "UC10"]),
    ("NFR02", "NFR", "Fallback: when Gemma fails or times out, search falls back to keyword rules", ["UC02", "UC03", "UC04", "UC10"]),
    ("NFR03", "NFR", "Uploaded images: JPEG, PNG or WebP only, at most 5 MB", ["UC04"]),
    ("NFR04", "NFR", "Layered architecture: the UI never accesses the database, AI sits behind the LlmClient interface", ["UC01"]),
    ("NFR05", "NFR", "Payment data: never store the full card number, only the last four digits and the authorisation code", ["UC07"]),
    ("NFR06", "NFR", "Runs offline on one machine: SQLite database, network only for the Gemma server", ["UC01"]),
    ("FR11", "FR", "Cancel my order while it is not shipped yet (PLACED or PROCESSING)", ["UC11"]),
    ("FR12", "FR", "The administrator adds paintings and changes price and stock", ["UC12"]),
    ("NFR07", "NFR", "Performance: text search answers within 2 seconds on the demo data; an AI call waits at most 15 seconds", ["UC02"]),
    ("FR13", "FR", "The administrator moves an order PLACED → PROCESSING → SHIPPED → DELIVERED", ["UC13"]),
    ("FR14", "FR", "Find a painting for my room: Gemma 4 reads the room photo (palette, style) to suggest paintings and preview them on the wall", ["UC14"]),
    ("NFR08", "NFR", "Voice privacy: audio is processed only on the machine by self-hosted Whisper; a 5-second sentence is transcribed within 3 seconds", ["UC03"]),
]
# Slide 02: "The system shall + action + object + condition", with priority (MoSCoW) and source stakeholder.
REQUIREMENT_DETAILS = {
    "FR01": ("Must", "Customer", "The system shall allow customers to search paintings by keyword or natural sentence and filter them by style, subject, colour, artist and maximum price."),
    "FR02": ("Should", "Customer", "The system shall accept a spoken search query, transcribe it with the self-hosted Whisper model and let the customer edit the transcript before searching."),
    "FR03": ("Should", "Customer", "The system shall return the paintings most similar to a photo uploaded by the customer, ranked by similarity."),
    "FR04": ("Could", "Customer", "The system shall combine a text query and an image in one search."),
    "FR05": ("Must", "Customer", "The system shall display painting details including artist, year, size, medium, price and current stock."),
    "FR06": ("Must", "Customer", "The system shall allow customers to add paintings to the cart, change quantities and remove cart lines."),
    "FR07": ("Must", "Customer, Warehouse", "The system shall create an order from the cart when the paintings are in stock, freeze the prices, decrease the stock and empty the cart."),
    "FR08": ("Must", "Customer", "The system shall allow customers to view their orders and the current status of each order."),
    "FR09": ("Must", "Customer", "The system shall allow customers to look up an order by id only when the order belongs to their account."),
    "FR10": ("Should", "Customer, Support staff", "The system shall answer shopping questions with an AI assistant that can call the painting search and order look-up functions."),
    "FR11": ("Should", "Customer", "The system shall allow customers to cancel an order before it is shipped."),
    "FR12": ("Must", "Administrator", "The system shall allow the administrator to add paintings and to update their price and stock."),
    "FR13": ("Must", "Administrator, Warehouse", "The system shall allow the administrator to update the processing and delivery status of orders."),
    "FR14": ("Could", "Customer", "The system shall suggest paintings that suit a room from a photo of the room and let the customer preview a painting on the wall."),
    "NFR01": ("Must", "Customer, Administrator", "The system shall take the identity from the signed-in session and check order ownership on the server."),
    "NFR02": ("Must", "Customer", "The system shall still find paintings with keyword rules when the Gemma service fails or times out."),
    "NFR03": ("Must", "Administrator", "The system shall reject uploaded images that are not JPEG, PNG or WebP or are larger than 5 MB."),
    "NFR04": ("Must", "Developer", "The system shall separate presentation, application, domain and infrastructure; the user interface shall not access the database directly."),
    "NFR05": ("Must", "Customer", "The system shall not store full card numbers; only the last four digits and the authorisation code are kept."),
    "NFR06": ("Should", "Lecturer, Developer", "The system shall run on one machine with a SQLite database and need the network only to call Gemma."),
    "NFR07": ("Should", "Customer", "The system shall return text search results within 2 seconds on the demo data."),
    "NFR08": ("Must", "Customer", "The system shall process audio on the local machine with self-hosted Whisper, never send audio outside, and transcribe a 5-second sentence within 3 seconds."),
}
ACTORS = [("Customer", "Customer of the gallery"), ("Administrator", "Gallery administrator"),
          ("Gemma 4 Service", "Gemma 4 AI service (L40S server)"), ("Payment Service", "Payment service (simulated)")]
# (id, name, actor, kind) with kind "abstract" for the generalised use case.
USE_CASES = [
    ("UC01", "Search Product", "Customer", "abstract"),
    ("UC02", "Search by Keyword", "Customer", ""),
    ("UC03", "Search by Voice", "Customer", ""),
    ("UC04", "Search by Image", "Customer", ""),
    ("UC05", "View Product", "Customer", ""),
    ("UC06", "Manage Cart", "Customer", ""),
    ("UC07", "Checkout", "Customer", ""),
    ("UC08", "View Order", "Customer", ""),
    ("UC09", "Search Order", "Customer", ""),
    ("UC10", "Ask Shopping Assistant", "Customer", ""),
    ("UC11", "Cancel Order", "Customer", ""),
    ("UC12", "Manage Products", "Administrator", ""),
    ("UC13", "Update Order Status", "Administrator", ""),
    ("UC14", "Find Painting for My Room", "Customer", ""),
]
# Secondary (supporting) actors per use case.
SUPPORTING_ACTORS = {"UC02": ["Gemma 4 Service"], "UC03": ["Gemma 4 Service"], "UC04": ["Gemma 4 Service"],
                     "UC10": ["Gemma 4 Service"], "UC07": ["Payment Service"], "UC14": ["Gemma 4 Service"]}
# (from, to, kind): generalization child -> parent, include base -> addition, extend extension -> base.
USE_CASE_LINKS = [
    ("UC02", "UC01", "Generalization"), ("UC03", "UC01", "Generalization"), ("UC04", "UC01", "Generalization"),
    ("UC07", "UC06", "Include"), ("UC10", "UC01", "Include"), ("UC10", "UC09", "Include"),
    ("UC05", "UC01", "Extend"), ("UC11", "UC08", "Extend"), ("UC14", "UC01", "Generalization"),
]
AI_USE_CASES = ["UC02", "UC03", "UC04", "UC10", "UC14"]  # use cases that use Gemma 4 or self-hosted Whisper
# Painting-shop versions of the A06 example queries (black running shoes, find Nike shoes under
# 100 dollars, show me products similar to this image, find my order 20261001, where is my latest order?).
DEMO_QUERIES = ["blue landscape paintings", "Monet paintings under 100 dollars", "show me paintings similar to this image",
                "find my order 20261001", "where is my latest order?"]

# --------------------------------------------------------------- 4.1 analysis
# The customer, cart, order, shipping and payment classes of Kiem tra 01; the
# product side is replaced by the painting shop of the demo (Product, Painting,
# Frame, Artist).
ANALYSIS = {
    "FullName": ["firstName: String", "middleName: String", "lastName: String"],
    "Customer": ["customerId: String", "email: String", "phone: String", "dateOfBirth: Date"],
    "Address": ["houseNumber: String", "street: String", "district: String", "city: String"],
    "CustomerVIP": ["vipLevel: int", "discountRate: float", "rewardPoints: int"],
    "CustomerNew": ["registeredDate: Date", "welcomeVoucher: String"],
    "Cart": ["cartId: String", "createdDate: Date", "updatedDate: Date"],
    "CartItem": ["quantity: int", "cartPrice: float"],
    "Order": ["orderId: String", "orderDate: Date", "status: String", "totalAmount: float"],
    "OrderItem": ["quantity: int", "unitPrice: float"],
    "Shipping": ["shippingId: String", "carrier: String", "trackingNumber: String",
                 "shippingFee: float", "status: String", "deliveredDate: Date"],
    "Payment": ["paymentId: String", "amount: float", "paymentDate: Date", "status: String"],
    "PayCash": ["cashReceived: float", "changeAmount: float"],
    "PayCredit": ["cardHolder: String", "bankName: String", "cardLast4: String", "authorizationCode: String"],
    "Product": ["productId: String", "name: String", "price: float", "stockQuantity: int", "imageUrl: String",
                "description: String"],
    "Artist": ["artistId: String", "name: String", "nationality: String", "lifeYears: String"],
    "Painting": ["style: String", "subject: String", "dominantColor: String", "medium: String",
                 "yearCreated: int", "widthCm: int", "heightCm: int"],
    "Frame": ["material: String", "color: String", "sizeLabel: String"],
}
ANALYSIS_ABSTRACT = {"Payment", "Product"}
NEW_IN_41 = {"Product", "Artist", "Painting", "Frame"}

# (child, parent)
ANALYSIS_GENERALIZATIONS = [
    ("CustomerVIP", "Customer"), ("CustomerNew", "Customer"),
    ("PayCash", "Payment"), ("PayCredit", "Payment"),
    ("Painting", "Product"), ("Frame", "Product"),
]

# kind: association | composition | aggregation (whole is always "a").
ANALYSIS_ASSOCIATIONS = [
    dict(a="Customer", b="FullName", name="has", a_mult="1", b_mult="1", kind="composition"),
    dict(a="Customer", b="Address", name="has", a_mult="1", b_mult="1..*", kind="aggregation"),
    dict(a="Customer", b="Cart", name="owns", a_mult="1", b_mult="0..1", kind="association"),
    dict(a="Customer", b="Order", name="places", a_mult="1", b_mult="0..*", kind="association"),
    dict(a="Cart", b="CartItem", name="contains", a_mult="1", b_mult="0..*", kind="composition"),
    dict(a="Order", b="OrderItem", name="contains", a_mult="1", b_mult="1..*", kind="composition"),
    dict(a="CartItem", b="Product", name="refers to", a_mult="0..*", b_mult="1", kind="association"),
    dict(a="OrderItem", b="Product", name="refers to", a_mult="0..*", b_mult="1", kind="association"),
    dict(a="Order", b="Shipping", name="is delivered by", a_mult="1", b_mult="0..1", kind="association"),
    dict(a="Shipping", b="Address", name="ships to", a_mult="0..*", b_mult="1", kind="association"),
    dict(a="Order", b="Payment", name="is paid by", a_mult="1", b_mult="0..*", kind="association"),
    dict(a="Artist", b="Painting", name="paints", a_mult="1", b_mult="0..*", kind="association"),
]
# (client, supplier, stereotype, name)
ANALYSIS_DEPENDENCIES = [("Cart", "Order", "create", "checkout")]


# ----------------------------------------------------------- 4.3 / 4.4 design
_ATTR = re.compile(r"^([+\-#~])\s*(\w+)\s*:\s*(.+)$")
_OP = re.compile(r"^([+\-#~])\s*(\w+)\((.*)\)\s*(?::\s*([^{]+?))?\s*(\{(\w+)\})?$")


def attr(text):
    vis, name, type_ = _ATTR.match(text.strip()).groups()
    return dict(vis=vis, name=name, type=type_.strip())


def op(text, body=None):
    vis, name, params, ret, _, flag = _OP.match(text.strip()).groups()
    plist = []
    for p in filter(None, (s.strip() for s in _split_params(params))):
        pname, ptype = (x.strip() for x in p.split(":", 1))
        plist.append((pname, ptype))
    return dict(vis=vis, name=name, params=plist, ret=(ret or "").strip() or None,
                static=flag == "static", abstract=flag == "abstract", body=body)


def _split_params(params):
    """Split on commas that are not inside generic brackets."""
    depth, cur = 0, ""
    for ch in params:
        depth += ch == "<"
        depth -= ch == ">"
        if ch == "," and depth == 0:
            yield cur
            cur = ""
        else:
            cur += ch
    yield cur


def cls(name, package, attrs=(), ops=(), extends=None, implements=(), kind="class",
        literals=(), abstract=False, doc=None):
    return dict(name=name, package=package, attrs=[attr(a) for a in attrs], ops=list(ops),
                extends=extends, implements=list(implements), kind=kind, literals=list(literals),
                abstract=abstract, doc=doc)


DESIGN = [
    # ---------------------------------------------------- domain.customer
    cls("FullName", "domain.customer",
        ["-firstName: String", "-middleName: String", "-lastName: String"],
        [op("+getDisplayName(): String", """
StringBuilder sb = new StringBuilder();
for (String part : new String[] {lastName, middleName, firstName}) {
    if (part != null && !part.trim().isEmpty()) {
        if (sb.length() > 0) sb.append(' ');
        sb.append(part.trim());
    }
}
return sb.toString();""")],
        doc="Value object: Vietnamese order is last + middle + first name."),
    cls("Address", "domain.customer",
        ["-addressId: String", "-houseNumber: String", "-street: String", "-district: String", "-city: String"],
        [op("+format(): String", 'return houseNumber + " " + street + ", " + district + ", " + city;')]),
    cls("Customer", "domain.customer",
        ["-customerId: String", "-email: String", "-phone: String", "-dateOfBirth: LocalDate"],
        [op("+getDisplayName(): String", "return fullName.getDisplayName();"),
         op("+getDiscountRate(): BigDecimal", "return BigDecimal.ZERO;"),
         op("+addAddress(address: Address): void", "addresses.add(address);"),
         op("+findAddress(addressId: String): Address", """
for (Address address : addresses) {
    if (address.getAddressId().equals(addressId)) return address;
}
throw new IllegalArgumentException("Address " + addressId + " does not belong to customer " + customerId);""")]),
    cls("CustomerVIP", "domain.customer",
        ["-vipLevel: int", "-discountRate: BigDecimal", "-rewardPoints: int"],
        [op("+getDiscountRate(): BigDecimal", "return discountRate;"),
         op("+addPoints(points: int): void", """
if (points < 0) throw new IllegalArgumentException("points must not be negative");
rewardPoints += points;""")],
        extends="Customer"),
    cls("CustomerNew", "domain.customer",
        ["-registeredDate: LocalDate", "-welcomeVoucher: String"],
        [op("+hasWelcomeVoucher(): boolean", "return welcomeVoucher != null && !welcomeVoucher.trim().isEmpty();")],
        extends="Customer"),

    # ----------------------------------------------------- domain.product
    cls("Product", "domain.product",
        ["-productId: String", "-name: String", "-price: BigDecimal", "-stockQuantity: int", "-imageUrl: String",
         "-description: String"],
        [op("+isAvailable(quantity: int): boolean", "return quantity > 0 && stockQuantity >= quantity;"),
         op("+decreaseStock(quantity: int): void", """
if (!isAvailable(quantity)) throw new IllegalStateException("Not enough stock for " + productId);
stockQuantity -= quantity;"""),
         op("+getCategory(): String {abstract}"),
         op("+keywords(): String", """
StringBuilder text = new StringBuilder(name).append(' ').append(getCategory());
if (description != null) text.append(' ').append(description);
return text.toString().toLowerCase();""")],
        abstract=True),
    cls("Artist", "domain.product",
        ["-artistId: String", "-name: String", "-nationality: String", "-lifeYears: String"],
        [op("+getDisplayName(): String", 'return lifeYears == null ? name : name + " (" + lifeYears + ")";')]),
    cls("Painting", "domain.product",
        ["-style: String", "-subject: String", "-dominantColor: String", "-medium: String", "-yearCreated: int",
         "-widthCm: int", "-heightCm: int"],
        [op("+getCategory(): String", 'return "PAINTING";'),
         op("+keywords(): String", """
StringBuilder text = new StringBuilder(super.keywords());
for (String part : new String[] {style, subject, dominantColor, medium, artist == null ? null : artist.getName()}) {
    if (part != null) text.append(' ').append(part.toLowerCase());
}
return text.toString();"""),
         op("+sizeLabel(): String", 'return widthCm + " x " + heightCm + " cm";')],
        extends="Product"),
    cls("Frame", "domain.product", ["-material: String", "-color: String", "-sizeLabel: String"],
        [op("+getCategory(): String", 'return "FRAME";'),
         op("+keywords(): String", 'return (super.keywords() + " " + material + " " + color).toLowerCase();')],
        extends="Product"),

    # -------------------------------------------------------- domain.cart
    cls("Cart", "domain.cart",
        ["-cartId: String", "-createdDate: LocalDateTime", "-updatedDate: LocalDateTime"],
        [op("+addItem(product: Product, quantity: int): void", """
if (quantity <= 0) throw new IllegalArgumentException("quantity must be greater than 0");
for (CartItem item : items) {
    if (item.getProduct().getProductId().equals(product.getProductId())) {
        item.increase(quantity);
        updatedDate = LocalDateTime.now();
        return;
    }
}
items.add(new CartItem(product, quantity));
updatedDate = LocalDateTime.now();"""),
         op("+updateQuantity(productId: String, quantity: int): void", """
if (quantity <= 0) {
    removeItem(productId);
    return;
}
for (CartItem item : items) {
    if (item.getProduct().getProductId().equals(productId)) item.setQuantity(quantity);
}
updatedDate = LocalDateTime.now();"""),
         op("+removeItem(productId: String): void", """
items.removeIf(item -> item.getProduct().getProductId().equals(productId));
updatedDate = LocalDateTime.now();"""),
         op("+calculateTotal(): BigDecimal", """
BigDecimal total = BigDecimal.ZERO;
for (CartItem item : items) total = total.add(item.getSubtotal());
return total;"""),
         op("+isEmpty(): boolean", "return items.isEmpty();"),
         op("+clear(): void", """
items.clear();
updatedDate = LocalDateTime.now();""")]),
    cls("CartItem", "domain.cart",
        ["-quantity: int", "-cartPrice: BigDecimal"],
        [op("+CartItem(product: Product, quantity: int)", """
this.product = product;
this.quantity = quantity;
this.cartPrice = product.getPrice();"""),
         op("+getSubtotal(): BigDecimal", "return cartPrice.multiply(BigDecimal.valueOf(quantity));"),
         op("+increase(quantity: int): void", "this.quantity += quantity;")]),

    # ------------------------------------------------------- domain.order
    cls("OrderStatus", "domain.order", kind="enum",
        literals=["PLACED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]),
    cls("Order", "domain.order",
        ["-orderId: String", "-orderDate: LocalDateTime", "-status: OrderStatus", "-totalAmount: BigDecimal"],
        [op("+addItem(item: OrderItem): void", "items.add(item);"),
         op("+addPayment(payment: Payment): void", "payments.add(payment);"),
         op("+calculateTotal(discountRate: BigDecimal): BigDecimal", """
BigDecimal subtotal = BigDecimal.ZERO;
for (OrderItem item : items) subtotal = subtotal.add(item.getSubtotal());
BigDecimal discount = subtotal.multiply(discountRate);
BigDecimal fee = shipping == null ? BigDecimal.ZERO : shipping.getShippingFee();
totalAmount = subtotal.subtract(discount).add(fee).max(BigDecimal.ZERO);
return totalAmount;"""),
         op("+cancel(): void", """
if (status != OrderStatus.PLACED && status != OrderStatus.PROCESSING)
    throw new IllegalStateException("Only placed or processing orders can be cancelled");
status = OrderStatus.CANCELLED;"""),
         op("+advanceTo(next: OrderStatus): void", """
boolean allowed = (status == OrderStatus.PLACED && next == OrderStatus.PROCESSING)
        || (status == OrderStatus.PROCESSING && next == OrderStatus.SHIPPED)
        || (status == OrderStatus.SHIPPED && next == OrderStatus.DELIVERED);
if (!allowed) throw new IllegalStateException("Cannot move order " + orderId + " from " + status + " to " + next);
status = next;"""),
         op("+isOwnedBy(customerId: String): boolean",
            "return customer != null && customer.getCustomerId().equals(customerId);")]),
    cls("OrderItem", "domain.order",
        ["-quantity: int", "-unitPrice: BigDecimal"],
        [op("+fromCartItem(item: CartItem, current: Product): OrderItem {static}", """
OrderItem orderItem = new OrderItem();
orderItem.product = current;
orderItem.quantity = item.getQuantity();
orderItem.unitPrice = current.getPrice();
return orderItem;"""),
         op("+getSubtotal(): BigDecimal", "return unitPrice.multiply(BigDecimal.valueOf(quantity));")]),
    cls("ShippingStatus", "domain.order", kind="enum", literals=["PREPARING", "IN_TRANSIT", "DELIVERED"]),
    cls("Shipping", "domain.order",
        ["-shippingId: String", "-carrier: String", "-trackingNumber: String", "-shippingFee: BigDecimal",
         "-status: ShippingStatus", "-deliveredDate: LocalDate"],
        [op("+updateStatus(newStatus: ShippingStatus): void", "status = newStatus;"),
         op("+markDelivered(date: LocalDate): void", """
status = ShippingStatus.DELIVERED;
deliveredDate = date;""")]),

    # ----------------------------------------------------- domain.payment
    cls("PaymentStatus", "domain.payment", kind="enum", literals=["PENDING", "SUCCEEDED", "FAILED"]),
    cls("Payment", "domain.payment",
        ["-paymentId: String", "-amount: BigDecimal", "-paymentDate: LocalDateTime", "-status: PaymentStatus"],
        [op("+process(): boolean {abstract}"),
         op("+markSucceeded(): void", """
status = PaymentStatus.SUCCEEDED;
paymentDate = LocalDateTime.now();"""),
         op("+markFailed(): void", "status = PaymentStatus.FAILED;")],
        abstract=True),
    cls("PayCash", "domain.payment",
        ["-cashReceived: BigDecimal", "-changeAmount: BigDecimal"],
        [op("+process(): boolean", """
if (cashReceived == null || cashReceived.compareTo(getAmount()) < 0) {
    markFailed();
    return false;
}
changeAmount = cashReceived.subtract(getAmount());
markSucceeded();
return true;""")],
        extends="Payment"),
    cls("PayCredit", "domain.payment",
        ["-cardHolder: String", "-bankName: String", "-cardLast4: String", "-authorizationCode: String"],
        [op("+process(): boolean", """
// The card is authorised by the payment provider; only its code is kept here.
if (authorizationCode == null || authorizationCode.trim().isEmpty()) {
    markFailed();
    return false;
}
markSucceeded();
return true;"""),
         op("+maskedCard(): String", 'return "**** **** **** " + cardLast4;')],
        extends="Payment"),

    # ------------------------------------------- infrastructure.repository
    # Names follow slide A05 (CartRepository, OrderRepository) and A06
    # (ProductRepository.all_products, OrderRepository.find_order).
    cls("CustomerRepository", "infrastructure.repository", kind="interface",
        ops=[op("+findById(customerId: String): Customer"),
             op("+allCustomers(): List<Customer>"),
             op("+saveAddress(customerId: String, address: Address): Address")]),
    cls("ProductRepository", "infrastructure.repository", kind="interface",
        ops=[op("+allProducts(): List<Product>"),
             op("+findById(productId: String): Product"),
             op("+decreaseStock(productId: String, quantity: int): void"),
             op("+save(product: Product): void")]),
    cls("CartRepository", "infrastructure.repository", kind="interface",
        ops=[op("+findById(cartId: String): Cart"),
             op("+findByCustomerId(customerId: String): Cart"),
             op("+save(cart: Cart): void"),
             op("+clear(cartId: String): void")]),
    cls("OrderRepository", "infrastructure.repository", kind="interface",
        ops=[op("+findOrder(orderId: String): Order"),
             op("+findByCustomer(customerId: String): List<Order>"),
             op("+allOrders(): List<Order>"),
             op("+save(order: Order): void"),
             op("+updateStatus(orderId: String, status: OrderStatus): void")]),
    cls("Database", "infrastructure.repository.sqlite", ["-url: String"],
        [op("+Database(url: String)"),
         op("+getConnection(): Connection"),
         op("+initialize(schemaSql: String, seedSql: String): void")],
        doc="SQLite file database (ecom.db): schema and seed come from db/*.sql."),
    cls("SqliteCustomerRepository", "infrastructure.repository.sqlite", ["-database: Database"],
        [op("+SqliteCustomerRepository(database: Database)"),
         op("+findById(customerId: String): Customer"),
         op("+allCustomers(): List<Customer>"),
         op("+saveAddress(customerId: String, address: Address): Address")], implements=["CustomerRepository"]),
    cls("SqliteProductRepository", "infrastructure.repository.sqlite", ["-database: Database"],
        [op("+SqliteProductRepository(database: Database)"),
         op("+allProducts(): List<Product>"),
         op("+findById(productId: String): Product"),
         op("+decreaseStock(productId: String, quantity: int): void"),
         op("+save(product: Product): void")], implements=["ProductRepository"]),
    cls("SqliteCartRepository", "infrastructure.repository.sqlite", ["-database: Database"],
        [op("+SqliteCartRepository(database: Database)"),
         op("+findById(cartId: String): Cart"),
         op("+findByCustomerId(customerId: String): Cart"),
         op("+save(cart: Cart): void"),
         op("+clear(cartId: String): void")], implements=["CartRepository"]),
    cls("SqliteOrderRepository", "infrastructure.repository.sqlite", ["-database: Database"],
        [op("+SqliteOrderRepository(database: Database)"),
         op("+findOrder(orderId: String): Order"),
         op("+findByCustomer(customerId: String): List<Order>"),
         op("+allOrders(): List<Order>"),
         op("+save(order: Order): void"),
         op("+updateStatus(orderId: String, status: OrderStatus): void")], implements=["OrderRepository"]),

    # ---------------------------------------------- infrastructure.search
    cls("VectorIndex", "infrastructure.search", ["-productEmbeddings: Map<String, double[]>"],
        [op("+build(products: List<Product>): void"),
         op("+embedProduct(product: Product): double[]"),
         op("+toVector(style: String, subject: String, color: String): double[] {static}"),
         op("+cosineSimilarity(a: double[], b: double[]): double {static}"),
         op("+nearest(queryEmbedding: double[], k: int): Map<String, Double>")],
        doc="A06 slide: cosine_similarity(a, b) and search over product embeddings."),

    # -------------------------------------------------- infrastructure.ai
    cls("ToolCall", "infrastructure.ai", ["-id: String", "-name: String", "-arguments: String"],
        [op("+ToolCall(id: String, name: String, arguments: String)")]),
    cls("LlmReply", "infrastructure.ai", ["-content: String", "-toolCalls: List<ToolCall>"],
        [op("+LlmReply(content: String, toolCalls: List<ToolCall>)"),
         op("+hasToolCalls(): boolean")]),
    cls("LlmClient", "infrastructure.ai", kind="interface",
        ops=[op("+chat(messages: List<Map<String, Object>>, tools: List<Map<String, Object>>): LlmReply"),
             op("+isAvailable(): boolean")]),
    cls("SpeechClient", "infrastructure.ai", kind="interface",
        ops=[op("+transcribe(audio: byte[], language: String): String"),
             op("+isAvailable(): boolean")]),
    cls("WhisperClient", "infrastructure.ai", ["-baseUrl: String", "-model: String", "-timeoutSeconds: int"],
        [op("+WhisperClient(baseUrl: String, model: String, timeoutSeconds: int)"),
         op("+transcribe(audio: byte[], language: String): String"),
         op("+isAvailable(): boolean")], implements=["SpeechClient"],
        doc="Client of the self-hosted Whisper voice server (demo/voice-server, faster-whisper, localhost:9000)."),
    cls("GemmaClient", "infrastructure.ai",
        ["-baseUrl: String", "-apiKey: String", "-model: String", "-timeoutSeconds: int"],
        [op("+GemmaClient(baseUrl: String, apiKey: String, model: String, timeoutSeconds: int)"),
         op("+chat(messages: List<Map<String, Object>>, tools: List<Map<String, Object>>): LlmReply"),
         op("+isAvailable(): boolean")], implements=["LlmClient"],
        doc="OpenAI-compatible client of Gemma 4 on the L40S server (HUONG_DAN_GOI_GEMMA4.md)."),

    # ------------------------------------------------- application.search
    # Class and method names follow the Assignment 06 slide code:
    # QueryService.text_query/voice_query/image_query, SpeechService.transcribe,
    # SearchService.search_text, RankingService, VectorIndex.
    cls("CommonQuery", "application.search",
        ["-type: String", "-query: String", "-embedding: double[]", "-style: String", "-subject: String",
         "-color: String", "-artist: String", "-maxPrice: BigDecimal", "-aiUsed: boolean"],
        [op("+CommonQuery(type: String, query: String)")]),
    cls("SearchResult", "application.search",
        ["-product: Product", "-textScore: double", "-imageScore: double", "-businessScore: double",
         "-score: double", "-reason: String"],
        [op("+SearchResult(product: Product)")]),
    cls("QueryService", "application.search", ["-llmClient: LlmClient"],
        [op("+QueryService(llmClient: LlmClient)"),
         op("+textQuery(text: String): CommonQuery"),
         op("+voiceQuery(text: String): CommonQuery"),
         op("+imageQuery(embedding: double[]): CommonQuery"),
         op("-understand(query: CommonQuery): void"),
         op("-parseRules(query: CommonQuery): void")]),
    cls("SpeechService", "application.search", ["-speechClient: SpeechClient"],
        [op("+SpeechService(speechClient: SpeechClient)"),
         op("+transcribe(audioInput: byte[]): String")],
        doc="A06 SpeechService.transcribe(audio_input): real speech-to-text through self-hosted Whisper."),
    cls("ImageService", "application.search", ["-llmClient: LlmClient"],
        [op("+ImageService(llmClient: LlmClient)"),
         op("+embed(image: byte[]): double[]"),
         op("+describe(image: byte[], purpose: String): Map<String, String>")]),
    cls("RankingService", "application.search", ["-alpha: double", "-beta: double", "-gamma: double"],
        [op("+RankingService(alpha: double, beta: double, gamma: double)"),
         op("+rank(query: CommonQuery, candidates: List<SearchResult>, limit: int): List<SearchResult>"),
         op("+businessScore(product: Product): double")],
        doc="S(x|q) = alpha*Stext + beta*Simage + gamma*Sbusiness (slide A06, eq. 6)."),
    cls("SearchService", "application.search",
        ["-repository: ProductRepository", "-queryService: QueryService",
         "-imageService: ImageService", "-vectorIndex: VectorIndex", "-rankingService: RankingService"],
        [op("+SearchService(repository: ProductRepository, queryService: QueryService, imageService: ImageService, vectorIndex: VectorIndex, rankingService: RankingService)"),
         op("+searchText(text: String): List<SearchResult>"),
         op("+searchVoice(transcript: String): List<SearchResult>"),
         op("+searchImage(image: byte[]): List<SearchResult>"),
         op("+searchRoom(image: byte[]): List<SearchResult>"),
         op("+describeRoom(image: byte[]): Map<String, String>"),
         op("+searchMultimodal(text: String, image: byte[]): List<SearchResult>"),
         op("-retrieve(query: CommonQuery): List<SearchResult>")]),

    # ------------------------------------------------ application.service
    cls("CartService", "application.service",
        ["-cartRepository: CartRepository", "-productRepository: ProductRepository"],
        [op("+CartService(cartRepository: CartRepository, productRepository: ProductRepository)"),
         op("+addToCart(customerId: String, productId: String, quantity: int): Cart"),
         op("+updateQuantity(customerId: String, productId: String, quantity: int): Cart"),
         op("+removeItem(customerId: String, productId: String): Cart"),
         op("+viewCart(customerId: String): Cart")]),
    cls("CheckoutService", "application.service",
        ["-cartRepository: CartRepository", "-orderRepository: OrderRepository",
         "-productRepository: ProductRepository", "-customerRepository: CustomerRepository"],
        [op("+CheckoutService(cartRepository: CartRepository, orderRepository: OrderRepository, productRepository: ProductRepository, customerRepository: CustomerRepository)"),
         op("+checkout(cartId: String, customerId: String, addressId: String, payment: Payment): Order"),
         op("+addAddress(customerId: String, address: Address): Address")],
        doc="Slide A05: CheckoutService.checkout(cartID) : Order. addAddress saves a delivery address typed at checkout."),
    cls("OrderService", "application.service", ["-orderRepository: OrderRepository"],
        [op("+OrderService(orderRepository: OrderRepository)"),
         op("+getOrder(customerId: String, orderId: String): Order"),
         op("+listOrders(customerId: String): List<Order>"),
         op("+latestOrder(customerId: String): Order"),
         op("+cancelOrder(customerId: String, orderId: String): void"),
         op("+listAllOrders(): List<Order>"),
         op("+updateStatus(orderId: String, status: OrderStatus): Order")]),
    cls("ProductService", "application.service", ["-productRepository: ProductRepository"],
        [op("+ProductService(productRepository: ProductRepository)"),
         op("+listProducts(): List<Product>"),
         op("+updatePriceAndStock(productId: String, price: BigDecimal, stockQuantity: int): Product"),
         op("+addPainting(painting: Painting): Painting")]),
    cls("AssistantReply", "application.service",
        ["-answer: String", "-toolsUsed: List<String>", "-aiUsed: boolean"],
        [op("+AssistantReply(answer: String, toolsUsed: List<String>, aiUsed: boolean)")]),
    cls("AssistantService", "application.service",
        ["-llmClient: LlmClient", "-searchService: SearchService", "-orderService: OrderService"],
        [op("+AssistantService(llmClient: LlmClient, searchService: SearchService, orderService: OrderService)"),
         op("+ask(customerId: String, message: String): AssistantReply"),
         op("-tools(): List<Map<String, Object>>"),
         op("-runTool(customerId: String, call: ToolCall): String")],
        doc="Shopping assistant: Gemma 4 chooses a tool, the service runs it with the session customer."),

    # ---------------------------------------------- presentation.controller
    cls("SearchController", "presentation.controller",
        ["-searchService: SearchService", "-speechService: SpeechService"],
        [op("+SearchController(searchService: SearchService, speechService: SpeechService)"),
         op("+search(text: String): List<SearchResult>"),
         op("+transcribe(audioInput: byte[]): String"),
         op("+searchVoice(transcript: String): List<SearchResult>"),
         op("+searchImage(image: byte[]): List<SearchResult>"),
         op("+searchRoom(image: byte[]): List<SearchResult>"),
         op("+describeRoom(image: byte[]): Map<String, String>"),
         op("+searchMultimodal(text: String, image: byte[]): List<SearchResult>")]),
    cls("CartController", "presentation.controller", ["-cartService: CartService"],
        [op("+CartController(cartService: CartService)"),
         op("+addItem(customerId: String, productId: String, quantity: int): Cart"),
         op("+updateQuantity(customerId: String, productId: String, quantity: int): Cart"),
         op("+removeItem(customerId: String, productId: String): Cart"),
         op("+viewCart(customerId: String): Cart")]),
    cls("CheckoutController", "presentation.controller", ["-checkoutService: CheckoutService"],
        [op("+CheckoutController(checkoutService: CheckoutService)"),
         op("+checkout(customerId: String, cartId: String, addressId: String, paymentMethod: String): Order"),
         op("+addAddress(customerId: String, houseNumber: String, street: String, district: String, city: String): Address")]),
    cls("OrderController", "presentation.controller", ["-orderService: OrderService"],
        [op("+OrderController(orderService: OrderService)"),
         op("+viewOrder(customerId: String, orderId: String): Order"),
         op("+listOrders(customerId: String): List<Order>"),
         op("+cancelOrder(customerId: String, orderId: String): void")]),
    cls("AdminController", "presentation.controller",
        ["-productService: ProductService", "-orderService: OrderService"],
        [op("+AdminController(productService: ProductService, orderService: OrderService)"),
         op("+listProducts(): List<Product>"),
         op("+updateProduct(productId: String, price: BigDecimal, stockQuantity: int): Product"),
         op("+addPainting(painting: Painting): Painting"),
         op("+listAllOrders(): List<Order>"),
         op("+updateOrderStatus(orderId: String, status: String): Order")]),
    cls("AssistantController", "presentation.controller", ["-assistantService: AssistantService"],
        [op("+AssistantController(assistantService: AssistantService)"),
         op("+ask(customerId: String, message: String): AssistantReply")]),

    # ----------------------------------------------------- presentation.web
    cls("SessionManager", "presentation.web", ["-sessions: Map<String, String>"],
        [op("+login(customerId: String): String"),
         op("+customerOf(token: String): String"),
         op("+isAdmin(token: String): boolean")],
        doc="Demo login: the customer id always comes from the session, never from the request body."),
    cls("WebServer", "presentation.web",
        ["-port: int", "-sessionManager: SessionManager", "-searchController: SearchController",
         "-cartController: CartController", "-checkoutController: CheckoutController",
         "-orderController: OrderController", "-assistantController: AssistantController",
         "-adminController: AdminController"],
        [op("+WebServer(port: int, sessionManager: SessionManager, searchController: SearchController, cartController: CartController, checkoutController: CheckoutController, orderController: OrderController, assistantController: AssistantController, adminController: AdminController)"),
         op("+start(): void"),
         op("+stop(): void")]),
    cls("EcomApplication", "presentation.web", [],
        [op("+main(args: String[]): void {static}")],
        doc="Composition root, the Java counterpart of main.py in the A06 slide."),

    # ---------------------------------------------------- presentation.view
    # Browser components of the A06 presentation layer (web/js/*.js).
    cls("SearchUI", "presentation.view", kind="view",
        ops=[op("+submitText(text: String): void"), op("+submitVoice(transcript: String): void"),
             op("+submitImage(file: File): void"), op("+submitMultimodal(text: String, file: File): void")]),
    cls("VoiceInput", "presentation.view", kind="view",
        ops=[op("+start(): void"), op("+stop(): void"), op("+upload(audio: Blob): void"),
             op("+onTranscript(callback: Function): void")]),
    cls("RoomPreview", "presentation.view", kind="view",
        ops=[op("+chooseRoom(file: File): void"), op("+placePainting(product: Product): void"),
             op("+renderSuggestions(results: List<SearchResult>): void")]),
    cls("ImageUpload", "presentation.view", kind="view",
        ops=[op("+choose(file: File): void"), op("+validate(file: File): boolean"), op("+preview(): void")]),
    cls("SearchResultView", "presentation.view", kind="view",
        ops=[op("+render(results: List<SearchResult>): void"), op("+renderEmpty(message: String): void")]),
    cls("CartView", "presentation.view", kind="view",
        ops=[op("+render(cart: Cart): void"), op("+checkout(): void")]),
    cls("OrderView", "presentation.view", kind="view",
        ops=[op("+render(orders: List<Order>): void"), op("+lookup(orderId: String): void")]),
    cls("AssistantView", "presentation.view", kind="view",
        ops=[op("+send(message: String): void"), op("+render(reply: AssistantReply): void")]),
    cls("AdminView", "presentation.view", kind="view",
        ops=[op("+renderProducts(products: List<Product>): void"), op("+saveProduct(productId: String): void"),
             op("+renderOrders(orders: List<Order>): void"), op("+updateStatus(orderId: String, status: String): void")]),
]
DESIGN_BY_NAME = {c["name"]: c for c in DESIGN}

# Navigable associations of the design model. "src" holds a field named
# "role" whose type is "dst" (a List when the upper bound is *).
DESIGN_ASSOCIATIONS = [
    dict(src="Customer", dst="FullName", role="fullName", src_mult="1", mult="1", kind="composition", name="has"),
    dict(src="Customer", dst="Address", role="addresses", src_mult="1", mult="1..*", kind="aggregation", name="has"),
    dict(src="Cart", dst="Customer", role="owner", src_mult="0..1", mult="1", kind="association", name="owned by"),
    dict(src="Cart", dst="CartItem", role="items", src_mult="1", mult="0..*", kind="composition", name="contains"),
    dict(src="CartItem", dst="Product", role="product", src_mult="0..*", mult="1", kind="association", name="refers to"),
    dict(src="Order", dst="Customer", role="customer", src_mult="0..*", mult="1", kind="association", name="placed by"),
    dict(src="Order", dst="OrderItem", role="items", src_mult="1", mult="1..*", kind="composition", name="contains"),
    dict(src="OrderItem", dst="Product", role="product", src_mult="0..*", mult="1", kind="association", name="refers to"),
    dict(src="Order", dst="Shipping", role="shipping", src_mult="1", mult="0..1", kind="association", name="delivered by"),
    dict(src="Shipping", dst="Address", role="address", src_mult="0..*", mult="1", kind="association", name="ships to"),
    dict(src="Order", dst="Payment", role="payments", src_mult="1", mult="0..*", kind="association", name="paid by"),
    dict(src="Painting", dst="Artist", role="artist", src_mult="0..*", mult="1", kind="association", name="painted by"),
]

# (client, supplier, stereotype) dependencies shown in 4.3 and 4.4.
DESIGN_DEPENDENCIES_43 = [("OrderItem", "CartItem", "use")]
DESIGN_DEPENDENCIES_44 = [
    # presentation.view -> presentation.controller (HTTP / JSON)
    ("SearchUI", "VoiceInput", "use"), ("SearchUI", "ImageUpload", "use"), ("SearchUI", "SearchResultView", "use"),
    ("SearchUI", "SearchController", "use"), ("CartView", "CartController", "use"),
    ("CartView", "CheckoutController", "use"), ("OrderView", "OrderController", "use"),
    ("AssistantView", "AssistantController", "use"), ("AdminView", "AdminController", "use"),
    # presentation.web -> controllers
    ("WebServer", "SessionManager", "use"), ("WebServer", "SearchController", "use"),
    ("WebServer", "CartController", "use"), ("WebServer", "CheckoutController", "use"),
    ("WebServer", "OrderController", "use"), ("WebServer", "AssistantController", "use"),
    ("WebServer", "AdminController", "use"),
    # controllers -> application services
    ("SearchController", "SearchService", "use"), ("CartController", "CartService", "use"),
    ("CheckoutController", "CheckoutService", "use"), ("OrderController", "OrderService", "use"),
    ("AssistantController", "AssistantService", "use"),
    ("AdminController", "ProductService", "use"), ("AdminController", "OrderService", "use"),
    ("ProductService", "ProductRepository", "use"),
    # application -> domain / repositories / AI
    ("CartService", "CartRepository", "use"), ("CartService", "ProductRepository", "use"),
    ("CartService", "Cart", "use"),
    ("CheckoutService", "CartRepository", "use"), ("CheckoutService", "OrderRepository", "use"),
    ("CheckoutService", "ProductRepository", "use"), ("CheckoutService", "CustomerRepository", "use"),
    ("CheckoutService", "Order", "create"),
    ("OrderService", "OrderRepository", "use"),
    ("AssistantService", "LlmClient", "use"), ("AssistantService", "SearchService", "use"),
    ("AssistantService", "OrderService", "use"),
    ("SearchService", "ProductRepository", "use"), ("SearchService", "QueryService", "use"),
    ("SearchController", "SpeechService", "use"), ("SpeechService", "SpeechClient", "use"),
    ("RoomPreview", "SearchController", "use"), ("SearchService", "ImageService", "use"),
    ("SearchService", "VectorIndex", "use"), ("SearchService", "RankingService", "use"),
    ("QueryService", "LlmClient", "use"), ("ImageService", "LlmClient", "use"),
]

# The three layers of 4.4 (A06, reference essay) and the Java sub-packages that realise them. The domain
# classes are not a layer: they are the model shared by all three layers (cross-cutting).
LAYERS = [
    ("Presentation", "presentation", ["presentation.view", "presentation.controller", "presentation.web"]),
    ("Application", "application", ["application.service", "application.search"]),
    ("Data", "infrastructure", ["infrastructure.repository", "infrastructure.repository.sqlite",
                                "infrastructure.search", "infrastructure.ai"]),
]
DOMAIN_MODEL = ("Domain model", "domain", ["domain.customer", "domain.product", "domain.cart", "domain.order",
                                           "domain.payment"])
PACKAGE_GROUPS = LAYERS + [DOMAIN_MODEL]          # every Java package, layer by layer, then the shared model
LAYER_DEPENDENCIES = [("Presentation", "Application"), ("Application", "Data")]


# ---------------------------------------------------------- 4.2 tables (DB)
def col(name, type_, length=None, scale=None, pk=False, nullable=False, fk=None, unique=False, check=None):
    return dict(name=name, type=type_, length=length, scale=scale, pk=pk, nullable=nullable,
                fk=fk, unique=unique, check=check)


ID = ("varchar", 20)
MONEY = ("numeric", 12, 2)


def _id(name, **kw):
    return col(name, *ID, **kw)


def _money(name, **kw):
    return col(name, *MONEY, **kw)


# fk is "table.column"; source class in comments shows the class -> table mapping.
TABLES = [
    dict(name="customer", source="Customer + FullName", columns=[
        _id("customer_id", pk=True),
        col("first_name", "varchar", 50), col("middle_name", "varchar", 50, nullable=True),
        col("last_name", "varchar", 50), col("email", "varchar", 120, unique=True),
        col("phone", "varchar", 20, nullable=True), col("date_of_birth", "date", nullable=True)]),
    dict(name="customer_vip", source="CustomerVIP", columns=[
        _id("customer_id", pk=True, fk="customer.customer_id"),
        col("vip_level", "integer", check="vip_level >= 1"),
        col("discount_rate", "numeric", 4, 3, check="discount_rate >= 0 AND discount_rate < 1"),
        col("reward_points", "integer", check="reward_points >= 0")]),
    dict(name="customer_new", source="CustomerNew", columns=[
        _id("customer_id", pk=True, fk="customer.customer_id"),
        col("registered_date", "date"), col("welcome_voucher", "varchar", 30, nullable=True)]),
    dict(name="address", source="Address", columns=[
        _id("address_id", pk=True), _id("customer_id", fk="customer.customer_id"),
        col("house_number", "varchar", 20), col("street", "varchar", 100),
        col("district", "varchar", 60), col("city", "varchar", 60)]),
    dict(name="product", source="Product", columns=[
        _id("product_id", pk=True),
        col("product_type", "varchar", 12,
            check="product_type IN ('PAINTING','FRAME')"),
        col("name", "varchar", 200), _money("price", check="price >= 0"),
        col("stock_quantity", "integer", check="stock_quantity >= 0"),
        col("image_url", "varchar", 255, nullable=True), col("description", "varchar", 500, nullable=True)]),
    dict(name="artist", source="Artist", columns=[
        _id("artist_id", pk=True), col("name", "varchar", 120), col("nationality", "varchar", 60, nullable=True),
        col("life_years", "varchar", 20, nullable=True)]),
    dict(name="painting", source="Painting", columns=[
        _id("product_id", pk=True, fk="product.product_id"), _id("artist_id", fk="artist.artist_id"),
        col("style", "varchar", 40), col("subject", "varchar", 40), col("dominant_color", "varchar", 20),
        col("medium", "varchar", 60), col("year_created", "integer", check="year_created > 0"),
        col("width_cm", "integer", check="width_cm > 0"), col("height_cm", "integer", check="height_cm > 0")]),
    dict(name="frame", source="Frame", columns=[
        _id("product_id", pk=True, fk="product.product_id"), col("material", "varchar", 40),
        col("color", "varchar", 20), col("size_label", "varchar", 20)]),
    dict(name="product_feature", source="VectorIndex (search)", columns=[
        _id("product_id", pk=True, fk="product.product_id"), col("model_version", "varchar", 40),
        col("feature_vector", "bytea"), col("updated_at", "timestamp")]),
    dict(name="cart", source="Cart", columns=[
        _id("cart_id", pk=True), _id("customer_id", fk="customer.customer_id", unique=True),
        col("created_date", "timestamp"), col("updated_date", "timestamp")]),
    dict(name="cart_item", source="CartItem", columns=[
        _id("cart_id", pk=True, fk="cart.cart_id"), _id("product_id", pk=True, fk="product.product_id"),
        col("quantity", "integer", check="quantity > 0"), _money("cart_price", check="cart_price >= 0")]),
    dict(name="orders", source="Order", columns=[
        _id("order_id", pk=True), _id("customer_id", fk="customer.customer_id"),
        col("order_date", "timestamp"),
        col("status", "varchar", 12,
            check="status IN ('PLACED','PROCESSING','SHIPPED','DELIVERED','CANCELLED')"),
        _money("total_amount", check="total_amount >= 0")]),
    dict(name="order_item", source="OrderItem", columns=[
        _id("order_id", pk=True, fk="orders.order_id"), _id("product_id", pk=True, fk="product.product_id"),
        col("quantity", "integer", check="quantity > 0"), _money("unit_price", check="unit_price >= 0")]),
    dict(name="shipping", source="Shipping", columns=[
        _id("shipping_id", pk=True), _id("order_id", fk="orders.order_id", unique=True),
        _id("address_id", fk="address.address_id"), col("carrier", "varchar", 60, nullable=True),
        col("tracking_number", "varchar", 40, nullable=True), _money("shipping_fee", check="shipping_fee >= 0"),
        col("status", "varchar", 12, check="status IN ('PREPARING','IN_TRANSIT','DELIVERED')"),
        col("delivered_date", "date", nullable=True)]),
    dict(name="payment", source="Payment", columns=[
        _id("payment_id", pk=True), _id("order_id", fk="orders.order_id"),
        col("method", "varchar", 6, check="method IN ('CASH','CREDIT')"),
        _money("amount", check="amount >= 0"), col("payment_date", "timestamp", nullable=True),
        col("status", "varchar", 10, check="status IN ('PENDING','SUCCEEDED','FAILED')")]),
    dict(name="pay_cash", source="PayCash", columns=[
        _id("payment_id", pk=True, fk="payment.payment_id"),
        _money("cash_received", nullable=True), _money("change_amount", nullable=True)]),
    dict(name="pay_credit", source="PayCredit", columns=[
        _id("payment_id", pk=True, fk="payment.payment_id"), col("card_holder", "varchar", 100),
        col("bank_name", "varchar", 60), col("card_last4", "char", 4),
        col("authorization_code", "varchar", 40, nullable=True)]),
]

# Relationship name and multiplicities of every foreign key: (child.column) -> (name, parent_mult, child_mult)
FK_LABELS = {
    "customer_vip.customer_id": ("is a", "1", "0..1"),
    "customer_new.customer_id": ("is a", "1", "0..1"),
    "address.customer_id": ("has", "1", "1..*"),
    "painting.product_id": ("is a", "1", "0..1"),
    "painting.artist_id": ("paints", "1", "0..*"),
    "frame.product_id": ("is a", "1", "0..1"),
    "product_feature.product_id": ("indexed by", "1", "0..1"),
    "cart.customer_id": ("owns", "1", "0..1"),
    "cart_item.cart_id": ("contains", "1", "0..*"),
    "cart_item.product_id": ("refers to", "1", "0..*"),
    "orders.customer_id": ("places", "1", "0..*"),
    "order_item.order_id": ("contains", "1", "1..*"),
    "order_item.product_id": ("refers to", "1", "0..*"),
    "shipping.order_id": ("is delivered by", "1", "0..1"),
    "shipping.address_id": ("ships to", "1", "0..*"),
    "payment.order_id": ("is paid by", "1", "0..*"),
    "pay_cash.payment_id": ("is a", "1", "0..1"),
    "pay_credit.payment_id": ("is a", "1", "0..1"),
}


def foreign_keys():
    """Yield (child_table, column, parent_table, parent_column) in table order."""
    for table in TABLES:
        for c in table["columns"]:
            if c["fk"]:
                parent, parent_col = c["fk"].split(".")
                yield table["name"], c["name"], parent, parent_col


if __name__ == "__main__":
    assert len(ANALYSIS) == 17, len(ANALYSIS)
    names = set(DESIGN_BY_NAME)
    for a in DESIGN_ASSOCIATIONS:
        assert a["src"] in names and a["dst"] in names, a
    for c, s, _ in DESIGN_DEPENDENCIES_43 + DESIGN_DEPENDENCIES_44:
        assert c in names and s in names, (c, s)
    tables = {t["name"]: {c["name"] for c in t["columns"]} for t in TABLES}
    for child, column, parent, parent_col in foreign_keys():
        assert parent in tables and parent_col in tables[parent], (child, column)
        assert f"{child}.{column}" in FK_LABELS, (child, column)
    print(f"analysis={len(ANALYSIS)} design={len(DESIGN)} tables={len(TABLES)} fks={len(list(foreign_keys()))}")

"""Single source of truth for Chapter 4 (Design).

The analysis model (4.1), the data model and tables (4.2), the design classes
(4.3), the layers (4.4) and the generated Java code (4.5) are all read from
this file, so the VP diagrams, the SQL and the code cannot drift apart.

Member strings use UML notation: "-name: Type" for attributes and
"+name(p: T, q: U): R {static|abstract}" for operations; an operation whose
name equals its class is a constructor.
"""
import re

BASE_PACKAGE = "com.ptit.ecom"

# --------------------------------------------------------------- 4.1 analysis
# The 19 classes of Kiem tra 01 plus the abstract Product introduced in 4.1.
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
    "Product": ["productId: String", "name: String", "price: float", "stockQuantity: int", "imageUrl: String"],
    "Book": ["author: String", "publisher: String"],
    "Clothes": ["brand: String", "size: String", "color: String", "material: String"],
    "Shoes": ["brand: String", "size: int", "color: String"],
    "Electronics": ["brand: String", "warrantyMonths: int"],
    "Laptop": ["cpu: String", "ram: String", "storage: String", "screenSize: float"],
    "Mobile": ["os: String", "camera: String", "screenSize: float", "batteryCapacity: int"],
}
ANALYSIS_ABSTRACT = {"Payment", "Product"}
NEW_IN_41 = {"Product"}

# (child, parent)
ANALYSIS_GENERALIZATIONS = [
    ("CustomerVIP", "Customer"), ("CustomerNew", "Customer"),
    ("PayCash", "Payment"), ("PayCredit", "Payment"),
    ("Book", "Product"), ("Clothes", "Product"), ("Shoes", "Product"), ("Electronics", "Product"),
    ("Laptop", "Electronics"), ("Mobile", "Electronics"),
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
        ["-productId: String", "-name: String", "-price: BigDecimal", "-stockQuantity: int", "-imageUrl: String"],
        [op("+isAvailable(quantity: int): boolean", "return quantity > 0 && stockQuantity >= quantity;"),
         op("+decreaseStock(quantity: int): void", """
if (!isAvailable(quantity)) throw new IllegalStateException("Not enough stock for " + productId);
stockQuantity -= quantity;"""),
         op("+getCategory(): String {abstract}")],
        abstract=True),
    cls("Book", "domain.product", ["-author: String", "-publisher: String"],
        [op("+getCategory(): String", 'return "BOOK";')], extends="Product"),
    cls("Clothes", "domain.product", ["-brand: String", "-size: String", "-color: String", "-material: String"],
        [op("+getCategory(): String", 'return "CLOTHES";')], extends="Product"),
    cls("Shoes", "domain.product", ["-brand: String", "-size: int", "-color: String"],
        [op("+getCategory(): String", 'return "SHOES";')], extends="Product"),
    cls("Electronics", "domain.product", ["-brand: String", "-warrantyMonths: int"],
        [op("+getCategory(): String", 'return "ELECTRONICS";')], extends="Product"),
    cls("Laptop", "domain.product", ["-cpu: String", "-ram: String", "-storage: String", "-screenSize: double"],
        [op("+getCategory(): String", 'return "LAPTOP";')], extends="Electronics"),
    cls("Mobile", "domain.product", ["-os: String", "-camera: String", "-screenSize: double", "-batteryCapacity: int"],
        [op("+getCategory(): String", 'return "MOBILE";')], extends="Electronics"),

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

    # ------------------------------------------------- infrastructure.dao
    cls("CustomerDAO", "infrastructure.dao", kind="interface",
        ops=[op("+findById(customerId: String): Customer")]),
    cls("ProductDAO", "infrastructure.dao", kind="interface",
        ops=[op("+findById(productId: String): Product"),
             op("+searchByKeyword(keyword: String, limit: int): List<Product>"),
             op("+decreaseStock(productId: String, quantity: int): void")]),
    cls("CartDAO", "infrastructure.dao", kind="interface",
        ops=[op("+findByCustomerId(customerId: String): Cart"),
             op("+save(cart: Cart): void"),
             op("+clear(cartId: String): void")]),
    cls("OrderDAO", "infrastructure.dao", kind="interface",
        ops=[op("+save(order: Order): void"),
             op("+findByIdAndCustomer(orderId: String, customerId: String): Order"),
             op("+findByCustomer(customerId: String): List<Order>"),
             op("+updateStatus(orderId: String, status: OrderStatus): void")]),

    cls("JdbcCustomerDAO", "infrastructure.dao.jdbc", ["-dataSource: DataSource"],
        [op("+JdbcCustomerDAO(dataSource: DataSource)", "this.dataSource = dataSource;"),
         op("+findById(customerId: String): Customer")], implements=["CustomerDAO"]),
    cls("JdbcProductDAO", "infrastructure.dao.jdbc", ["-dataSource: DataSource"],
        [op("+JdbcProductDAO(dataSource: DataSource)", "this.dataSource = dataSource;"),
         op("+findById(productId: String): Product"),
         op("+searchByKeyword(keyword: String, limit: int): List<Product>"),
         op("+decreaseStock(productId: String, quantity: int): void", """
String sql = "UPDATE product SET stock_quantity = stock_quantity - ? "
        + "WHERE product_id = ? AND stock_quantity >= ?";
try (Connection connection = dataSource.getConnection();
     PreparedStatement statement = connection.prepareStatement(sql)) {
    statement.setInt(1, quantity);
    statement.setString(2, productId);
    statement.setInt(3, quantity);
    if (statement.executeUpdate() != 1) throw new IllegalStateException("Not enough stock for " + productId);
} catch (SQLException e) {
    throw new IllegalStateException("Cannot update stock of " + productId, e);
}""")], implements=["ProductDAO"]),
    cls("JdbcCartDAO", "infrastructure.dao.jdbc", ["-dataSource: DataSource"],
        [op("+JdbcCartDAO(dataSource: DataSource)", "this.dataSource = dataSource;"),
         op("+findByCustomerId(customerId: String): Cart"),
         op("+save(cart: Cart): void"),
         op("+clear(cartId: String): void", """
try (Connection connection = dataSource.getConnection();
     PreparedStatement statement = connection.prepareStatement("DELETE FROM cart_item WHERE cart_id = ?")) {
    statement.setString(1, cartId);
    statement.executeUpdate();
} catch (SQLException e) {
    throw new IllegalStateException("Cannot clear cart " + cartId, e);
}""")], implements=["CartDAO"]),
    cls("JdbcOrderDAO", "infrastructure.dao.jdbc", ["-dataSource: DataSource"],
        [op("+JdbcOrderDAO(dataSource: DataSource)", "this.dataSource = dataSource;"),
         op("+save(order: Order): void"),
         op("+findByIdAndCustomer(orderId: String, customerId: String): Order", """
// The customer id comes from the authenticated session, never from the request body.
String sql = "SELECT order_id, order_date, status, total_amount FROM orders "
        + "WHERE order_id = ? AND customer_id = ?";
try (Connection connection = dataSource.getConnection();
     PreparedStatement statement = connection.prepareStatement(sql)) {
    statement.setString(1, orderId);
    statement.setString(2, customerId);
    try (ResultSet rows = statement.executeQuery()) {
        if (!rows.next()) return null;
        Order order = new Order();
        order.setOrderId(rows.getString("order_id"));
        order.setOrderDate(rows.getTimestamp("order_date").toLocalDateTime());
        order.setStatus(OrderStatus.valueOf(rows.getString("status")));
        order.setTotalAmount(rows.getBigDecimal("total_amount"));
        return order;
    }
} catch (SQLException e) {
    throw new IllegalStateException("Cannot read order " + orderId, e);
}"""),
         op("+findByCustomer(customerId: String): List<Order>"),
         op("+updateStatus(orderId: String, status: OrderStatus): void")], implements=["OrderDAO"]),

    # ---------------------------------------------- infrastructure.search
    cls("VectorIndex", "infrastructure.search", ["-modelVersion: String"],
        [op("+embed(image: byte[]): float[]"),
         op("+nearest(vector: float[], k: int): Map<String, Double>")],
        doc="Adapter to the image-feature engine (Apple Vision in the A6 prototype)."),

    # ------------------------------------------------- application.search
    cls("CommonQuery", "application.search",
        ["-mode: String", "-text: String", "-imageVector: float[]", "-maxPrice: BigDecimal"],
        [op("+CommonQuery(mode: String, text: String, imageVector: float[], maxPrice: BigDecimal)", """
this.mode = mode;
this.text = text;
this.imageVector = imageVector;
this.maxPrice = maxPrice;""")]),
    cls("SearchResult", "application.search", ["-product: Product", "-score: double"],
        [op("+SearchResult(product: Product, score: double)", """
this.product = product;
this.score = score;""")]),
    cls("QueryService", "application.search", [],
        [op("+buildTextQuery(text: String): CommonQuery", """
String normalized = text == null ? "" : text.toLowerCase().trim().replaceAll("\\\\s+", " ");
if (normalized.isEmpty()) throw new IllegalArgumentException("Query text is required");
return new CommonQuery("text", normalized, null, null);"""),
         op("+buildVoiceQuery(transcript: String): CommonQuery", """
CommonQuery query = buildTextQuery(transcript);
return new CommonQuery("voice", query.getText(), null, null);"""),
         op("+buildImageQuery(imageVector: float[]): CommonQuery",
            'return new CommonQuery("image", "", imageVector, null);')]),
    cls("RankingService", "application.search", [],
        [op("+rank(query: CommonQuery, candidates: List<SearchResult>, limit: int): List<SearchResult>", """
List<SearchResult> ranked = new ArrayList<>();
for (SearchResult candidate : candidates) {
    if (candidate.getProduct().isAvailable(1)) ranked.add(candidate);
}
ranked.sort((a, b) -> Double.compare(b.getScore(), a.getScore()));
return ranked.subList(0, Math.min(limit, ranked.size()));""")]),
    cls("SearchService", "application.search",
        ["-queryService: QueryService", "-rankingService: RankingService", "-productDAO: ProductDAO",
         "-vectorIndex: VectorIndex"],
        [op("+SearchService(queryService: QueryService, rankingService: RankingService, productDAO: ProductDAO, vectorIndex: VectorIndex)", """
this.queryService = queryService;
this.rankingService = rankingService;
this.productDAO = productDAO;
this.vectorIndex = vectorIndex;"""),
         op("+searchText(text: String): List<SearchResult>", """
CommonQuery query = queryService.buildTextQuery(text);
List<SearchResult> candidates = new ArrayList<>();
for (Product product : productDAO.searchByKeyword(query.getText(), 100)) {
    candidates.add(new SearchResult(product, textScore(query.getText(), product.getName())));
}
return rankingService.rank(query, candidates, 5);"""),
         op("+searchVoice(transcript: String): List<SearchResult>", """
// A voice transcript follows the same retrieval path as typed text.
return searchText(queryService.buildVoiceQuery(transcript).getText());"""),
         op("+searchImage(image: byte[]): List<SearchResult>", """
CommonQuery query = queryService.buildImageQuery(vectorIndex.embed(image));
List<SearchResult> candidates = new ArrayList<>();
for (Map.Entry<String, Double> hit : vectorIndex.nearest(query.getImageVector(), 20).entrySet()) {
    Product product = productDAO.findById(hit.getKey());
    if (product != null) candidates.add(new SearchResult(product, hit.getValue()));
}
return rankingService.rank(query, candidates, 5);"""),
         op("-textScore(query: String, name: String): double {static}", """
String lower = name.toLowerCase();
String[] words = query.split(" ");
int hits = 0;
for (String word : words) {
    if (lower.contains(word)) hits++;
}
return (double) hits / words.length;""")]),

    # ------------------------------------------------ application.service
    cls("CartService", "application.service", ["-cartDAO: CartDAO", "-productDAO: ProductDAO"],
        [op("+CartService(cartDAO: CartDAO, productDAO: ProductDAO)", """
this.cartDAO = cartDAO;
this.productDAO = productDAO;"""),
         op("+addToCart(customerId: String, productId: String, quantity: int): Cart", """
Product product = productDAO.findById(productId);
if (product == null || !product.isAvailable(quantity))
    throw new IllegalArgumentException("Product is not available: " + productId);
Cart cart = cartDAO.findByCustomerId(customerId);
cart.addItem(product, quantity);
cartDAO.save(cart);
return cart;"""),
         op("+updateQuantity(customerId: String, productId: String, quantity: int): Cart", """
Cart cart = cartDAO.findByCustomerId(customerId);
cart.updateQuantity(productId, quantity);
cartDAO.save(cart);
return cart;"""),
         op("+removeItem(customerId: String, productId: String): Cart", """
Cart cart = cartDAO.findByCustomerId(customerId);
cart.removeItem(productId);
cartDAO.save(cart);
return cart;"""),
         op("+viewCart(customerId: String): Cart", "return cartDAO.findByCustomerId(customerId);")]),
    cls("CheckoutService", "application.service",
        ["-cartDAO: CartDAO", "-orderDAO: OrderDAO", "-productDAO: ProductDAO", "-customerDAO: CustomerDAO"],
        [op("+CheckoutService(cartDAO: CartDAO, orderDAO: OrderDAO, productDAO: ProductDAO, customerDAO: CustomerDAO)", """
this.cartDAO = cartDAO;
this.orderDAO = orderDAO;
this.productDAO = productDAO;
this.customerDAO = customerDAO;"""),
         op("+checkout(customerId: String, addressId: String, payment: Payment): Order", """
Cart cart = cartDAO.findByCustomerId(customerId);
if (cart == null || cart.isEmpty()) throw new IllegalStateException("Cart is empty");
Customer customer = customerDAO.findById(customerId);

Order order = new Order();
order.setCustomer(customer);
order.setOrderDate(LocalDateTime.now());
order.setStatus(OrderStatus.PLACED);
for (CartItem item : cart.getItems()) {
    // Price and stock are read again from the catalogue, not trusted from the cart.
    Product current = productDAO.findById(item.getProduct().getProductId());
    if (!current.isAvailable(item.getQuantity()))
        throw new IllegalStateException("Out of stock: " + current.getName());
    order.addItem(OrderItem.fromCartItem(item, current));
}

Shipping shipping = new Shipping();
shipping.setAddress(customer.findAddress(addressId));
shipping.setShippingFee(BigDecimal.ZERO);
shipping.setStatus(ShippingStatus.PREPARING);
order.setShipping(shipping);
order.calculateTotal(customer.getDiscountRate());

payment.setAmount(order.getTotalAmount());
payment.setStatus(PaymentStatus.PENDING);
order.addPayment(payment);

// save, decreaseStock and clear must run in one database transaction.
orderDAO.save(order);
for (OrderItem item : order.getItems())
    productDAO.decreaseStock(item.getProduct().getProductId(), item.getQuantity());
cartDAO.clear(cart.getCartId());
return order;""")]),
    cls("OrderService", "application.service", ["-orderDAO: OrderDAO"],
        [op("+OrderService(orderDAO: OrderDAO)", "this.orderDAO = orderDAO;"),
         op("+getOrder(customerId: String, orderId: String): Order", """
Order order = orderDAO.findByIdAndCustomer(orderId, customerId);
if (order == null) throw new IllegalArgumentException("Order not found: " + orderId);
return order;"""),
         op("+listOrders(customerId: String): List<Order>", "return orderDAO.findByCustomer(customerId);"),
         op("+cancelOrder(customerId: String, orderId: String): void", """
Order order = getOrder(customerId, orderId);
order.cancel();
orderDAO.updateStatus(orderId, order.getStatus());""")]),

    # ---------------------------------------------- presentation.controller
    cls("CartController", "presentation.controller", ["-cartService: CartService"],
        [op("+CartController(cartService: CartService)", "this.cartService = cartService;"),
         op("+addItem(customerId: String, productId: String, quantity: int): Cart",
            "return cartService.addToCart(customerId, productId, quantity);"),
         op("+viewCart(customerId: String): Cart", "return cartService.viewCart(customerId);")]),
    cls("CheckoutController", "presentation.controller", ["-checkoutService: CheckoutService"],
        [op("+CheckoutController(checkoutService: CheckoutService)", "this.checkoutService = checkoutService;"),
         op("+checkout(customerId: String, addressId: String, paymentMethod: String): Order", """
Payment payment = "CASH".equalsIgnoreCase(paymentMethod) ? new PayCash() : new PayCredit();
return checkoutService.checkout(customerId, addressId, payment);""")]),
    cls("OrderController", "presentation.controller", ["-orderService: OrderService"],
        [op("+OrderController(orderService: OrderService)", "this.orderService = orderService;"),
         op("+viewOrder(customerId: String, orderId: String): Order",
            "return orderService.getOrder(customerId, orderId);"),
         op("+listOrders(customerId: String): List<Order>", "return orderService.listOrders(customerId);"),
         op("+cancelOrder(customerId: String, orderId: String): void",
            "orderService.cancelOrder(customerId, orderId);")]),
    cls("SearchController", "presentation.controller", ["-searchService: SearchService"],
        [op("+SearchController(searchService: SearchService)", "this.searchService = searchService;"),
         op("+search(mode: String, text: String, image: byte[]): List<SearchResult>", """
if ("voice".equals(mode)) return searchService.searchVoice(text);
if ("image".equals(mode)) return searchService.searchImage(image);
return searchService.searchText(text);""")]),
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
]

# (client, supplier, stereotype) dependencies shown in 4.3 and 4.4.
DESIGN_DEPENDENCIES_43 = [("OrderItem", "CartItem", "use")]
DESIGN_DEPENDENCIES_44 = [
    ("CartController", "CartService", "use"),
    ("CheckoutController", "CheckoutService", "use"),
    ("OrderController", "OrderService", "use"),
    ("SearchController", "SearchService", "use"),
    ("CartService", "CartDAO", "use"),
    ("CartService", "ProductDAO", "use"),
    ("CheckoutService", "CartDAO", "use"),
    ("CheckoutService", "OrderDAO", "use"),
    ("CheckoutService", "ProductDAO", "use"),
    ("CheckoutService", "CustomerDAO", "use"),
    ("CheckoutService", "Order", "create"),
    ("CartService", "Cart", "use"),
    ("OrderService", "OrderDAO", "use"),
    ("SearchService", "QueryService", "use"),
    ("SearchService", "RankingService", "use"),
    ("SearchService", "ProductDAO", "use"),
    ("SearchService", "VectorIndex", "use"),
]

# Layer packages of 4.4 and the Java sub-packages that realise them.
LAYERS = [
    ("Presentation", "presentation", ["presentation.controller"]),
    ("Application", "application", ["application.service", "application.search"]),
    ("Domain", "domain", ["domain.customer", "domain.product", "domain.cart", "domain.order", "domain.payment"]),
    ("Infrastructure", "infrastructure", ["infrastructure.dao", "infrastructure.dao.jdbc", "infrastructure.search"]),
]
LAYER_DEPENDENCIES = [("Presentation", "Application"), ("Application", "Domain"),
                      ("Application", "Infrastructure"), ("Infrastructure", "Domain")]


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
            check="product_type IN ('BOOK','CLOTHES','SHOES','ELECTRONICS','LAPTOP','MOBILE')"),
        col("name", "varchar", 200), _money("price", check="price >= 0"),
        col("stock_quantity", "integer", check="stock_quantity >= 0"),
        col("image_url", "varchar", 255, nullable=True)]),
    dict(name="book", source="Book", columns=[
        _id("product_id", pk=True, fk="product.product_id"),
        col("author", "varchar", 120), col("publisher", "varchar", 120)]),
    dict(name="clothes", source="Clothes", columns=[
        _id("product_id", pk=True, fk="product.product_id"), col("brand", "varchar", 60),
        col("size", "varchar", 10), col("color", "varchar", 30), col("material", "varchar", 60)]),
    dict(name="shoes", source="Shoes", columns=[
        _id("product_id", pk=True, fk="product.product_id"), col("brand", "varchar", 60),
        col("size", "integer", check="size > 0"), col("color", "varchar", 30)]),
    dict(name="electronics", source="Electronics", columns=[
        _id("product_id", pk=True, fk="product.product_id"), col("brand", "varchar", 60),
        col("warranty_months", "integer", check="warranty_months >= 0")]),
    dict(name="laptop", source="Laptop", columns=[
        _id("product_id", pk=True, fk="electronics.product_id"), col("cpu", "varchar", 60),
        col("ram", "varchar", 20), col("storage", "varchar", 30), col("screen_size", "numeric", 4, 1)]),
    dict(name="mobile", source="Mobile", columns=[
        _id("product_id", pk=True, fk="electronics.product_id"), col("os", "varchar", 30),
        col("camera", "varchar", 60), col("screen_size", "numeric", 4, 1),
        col("battery_capacity", "integer", check="battery_capacity > 0")]),
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
    "book.product_id": ("is a", "1", "0..1"),
    "clothes.product_id": ("is a", "1", "0..1"),
    "shoes.product_id": ("is a", "1", "0..1"),
    "electronics.product_id": ("is a", "1", "0..1"),
    "laptop.product_id": ("is a", "1", "0..1"),
    "mobile.product_id": ("is a", "1", "0..1"),
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
    assert len(ANALYSIS) == 20, len(ANALYSIS)
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

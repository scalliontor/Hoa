-- Product
CREATE TABLE product (
    product_id     varchar(20)   NOT NULL PRIMARY KEY,
    product_type   varchar(12)   NOT NULL CHECK (product_type IN ('BOOK','CLOTHES','SHOES','ELECTRONICS','LAPTOP','MOBILE')),
    name           varchar(200)  NOT NULL,
    price          numeric(12,2) NOT NULL CHECK (price >= 0),
    stock_quantity integer       NOT NULL CHECK (stock_quantity >= 0),
    image_url      varchar(255)
);

-- CartItem
CREATE TABLE cart_item (
    cart_id    varchar(20)   NOT NULL REFERENCES cart (cart_id) ON DELETE CASCADE,
    product_id varchar(20)   NOT NULL REFERENCES product (product_id),
    quantity   integer       NOT NULL CHECK (quantity > 0),
    cart_price numeric(12,2) NOT NULL CHECK (cart_price >= 0),
    PRIMARY KEY (cart_id, product_id)
);

-- Order
CREATE TABLE orders (
    order_id     varchar(20)   NOT NULL PRIMARY KEY,
    customer_id  varchar(20)   NOT NULL REFERENCES customer (customer_id),
    order_date   timestamp     NOT NULL,
    status       varchar(12)   NOT NULL CHECK (status IN ('PLACED','PROCESSING','SHIPPED','DELIVERED','CANCELLED')),
    total_amount numeric(12,2) NOT NULL CHECK (total_amount >= 0)
);

-- OrderItem
CREATE TABLE order_item (
    order_id   varchar(20)   NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    product_id varchar(20)   NOT NULL REFERENCES product (product_id),
    quantity   integer       NOT NULL CHECK (quantity > 0),
    unit_price numeric(12,2) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, product_id)
);

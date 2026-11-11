-- SQLite schema of the Họa. shop, generated from tools/model.py (TABLES).
-- Table, column, key and constraint names are exactly those of the data model in section 4.2.

-- Customer + FullName
CREATE TABLE customer (
    customer_id varchar(20) NOT NULL,
    first_name varchar(50) NOT NULL,
    middle_name varchar(50),
    last_name varchar(50) NOT NULL,
    email varchar(120) NOT NULL UNIQUE,
    phone varchar(20),
    date_of_birth date,
    PRIMARY KEY (customer_id)
);

-- CustomerVIP
CREATE TABLE customer_vip (
    customer_id varchar(20) NOT NULL,
    vip_level integer NOT NULL CHECK (vip_level >= 1),
    discount_rate numeric(4,3) NOT NULL CHECK (discount_rate >= 0 AND discount_rate < 1),
    reward_points integer NOT NULL CHECK (reward_points >= 0),
    PRIMARY KEY (customer_id),
    FOREIGN KEY (customer_id) REFERENCES customer (customer_id) ON DELETE CASCADE
);

-- CustomerNew
CREATE TABLE customer_new (
    customer_id varchar(20) NOT NULL,
    registered_date date NOT NULL,
    welcome_voucher varchar(30),
    PRIMARY KEY (customer_id),
    FOREIGN KEY (customer_id) REFERENCES customer (customer_id) ON DELETE CASCADE
);

-- Address
CREATE TABLE address (
    address_id varchar(20) NOT NULL,
    customer_id varchar(20) NOT NULL,
    house_number varchar(20) NOT NULL,
    street varchar(100) NOT NULL,
    district varchar(60) NOT NULL,
    city varchar(60) NOT NULL,
    PRIMARY KEY (address_id),
    FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
);

-- Category
CREATE TABLE category (
    category_id varchar(20) NOT NULL,
    name varchar(60) NOT NULL UNIQUE,
    detail_kind varchar(12) NOT NULL CHECK (detail_kind IN ('PAINTING','FRAME')),
    description varchar(300),
    PRIMARY KEY (category_id)
);

-- Product
CREATE TABLE product (
    product_id varchar(20) NOT NULL,
    category_id varchar(20) NOT NULL,
    name varchar(200) NOT NULL,
    price numeric(12,2) NOT NULL CHECK (price >= 0),
    stock_quantity integer NOT NULL CHECK (stock_quantity >= 0),
    image_url varchar(255),
    description varchar(500),
    PRIMARY KEY (product_id),
    FOREIGN KEY (category_id) REFERENCES category (category_id)
);

-- Artist
CREATE TABLE artist (
    artist_id varchar(20) NOT NULL,
    name varchar(120) NOT NULL,
    nationality varchar(60),
    life_years varchar(20),
    PRIMARY KEY (artist_id)
);

-- Painting
CREATE TABLE painting (
    product_id varchar(20) NOT NULL,
    artist_id varchar(20) NOT NULL,
    style varchar(40) NOT NULL,
    subject varchar(40) NOT NULL,
    dominant_color varchar(20) NOT NULL,
    medium varchar(60) NOT NULL,
    year_created integer NOT NULL CHECK (year_created > 0),
    width_cm integer NOT NULL CHECK (width_cm > 0),
    height_cm integer NOT NULL CHECK (height_cm > 0),
    PRIMARY KEY (product_id),
    FOREIGN KEY (product_id) REFERENCES product (product_id) ON DELETE CASCADE,
    FOREIGN KEY (artist_id) REFERENCES artist (artist_id)
);

-- Frame
CREATE TABLE frame (
    product_id varchar(20) NOT NULL,
    material varchar(40) NOT NULL,
    color varchar(20) NOT NULL,
    size_label varchar(20) NOT NULL,
    PRIMARY KEY (product_id),
    FOREIGN KEY (product_id) REFERENCES product (product_id) ON DELETE CASCADE
);

-- VectorIndex (search)
CREATE TABLE product_feature (
    product_id varchar(20) NOT NULL,
    model_version varchar(40) NOT NULL,
    feature_vector blob NOT NULL,
    updated_at timestamp NOT NULL,
    PRIMARY KEY (product_id),
    FOREIGN KEY (product_id) REFERENCES product (product_id) ON DELETE CASCADE
);

-- Cart
CREATE TABLE cart (
    cart_id varchar(20) NOT NULL,
    customer_id varchar(20) NOT NULL UNIQUE,
    created_date timestamp NOT NULL,
    updated_date timestamp NOT NULL,
    PRIMARY KEY (cart_id),
    FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
);

-- CartItem
CREATE TABLE cart_item (
    cart_id varchar(20) NOT NULL,
    product_id varchar(20) NOT NULL,
    quantity integer NOT NULL CHECK (quantity > 0),
    cart_price numeric(12,2) NOT NULL CHECK (cart_price >= 0),
    PRIMARY KEY (cart_id, product_id),
    FOREIGN KEY (cart_id) REFERENCES cart (cart_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product (product_id)
);

-- Order
CREATE TABLE orders (
    order_id varchar(20) NOT NULL,
    customer_id varchar(20) NOT NULL,
    order_date timestamp NOT NULL,
    status varchar(12) NOT NULL CHECK (status IN ('PLACED','PROCESSING','SHIPPED','DELIVERED','CANCELLED')),
    total_amount numeric(12,2) NOT NULL CHECK (total_amount >= 0),
    PRIMARY KEY (order_id),
    FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
);

-- OrderItem
CREATE TABLE order_item (
    order_id varchar(20) NOT NULL,
    product_id varchar(20) NOT NULL,
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price numeric(12,2) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product (product_id)
);

-- Shipping
CREATE TABLE shipping (
    shipping_id varchar(20) NOT NULL,
    order_id varchar(20) NOT NULL UNIQUE,
    address_id varchar(20) NOT NULL,
    carrier varchar(60),
    tracking_number varchar(40),
    shipping_fee numeric(12,2) NOT NULL CHECK (shipping_fee >= 0),
    status varchar(12) NOT NULL CHECK (status IN ('PREPARING','IN_TRANSIT','DELIVERED')),
    delivered_date date,
    PRIMARY KEY (shipping_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id),
    FOREIGN KEY (address_id) REFERENCES address (address_id)
);

-- Payment
CREATE TABLE payment (
    payment_id varchar(20) NOT NULL,
    order_id varchar(20) NOT NULL,
    method varchar(6) NOT NULL CHECK (method IN ('CASH','CREDIT')),
    amount numeric(12,2) NOT NULL CHECK (amount >= 0),
    payment_date timestamp,
    status varchar(10) NOT NULL CHECK (status IN ('PENDING','SUCCEEDED','FAILED')),
    PRIMARY KEY (payment_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

-- PayCash
CREATE TABLE pay_cash (
    payment_id varchar(20) NOT NULL,
    cash_received numeric(12,2),
    change_amount numeric(12,2),
    PRIMARY KEY (payment_id),
    FOREIGN KEY (payment_id) REFERENCES payment (payment_id) ON DELETE CASCADE
);

-- PayCredit
CREATE TABLE pay_credit (
    payment_id varchar(20) NOT NULL,
    card_holder varchar(100) NOT NULL,
    bank_name varchar(60) NOT NULL,
    card_last4 char(4) NOT NULL,
    authorization_code varchar(40),
    PRIMARY KEY (payment_id),
    FOREIGN KEY (payment_id) REFERENCES payment (payment_id) ON DELETE CASCADE
);

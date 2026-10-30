CREATE TABLE product (
    product_id varchar(20) NOT NULL,
    product_type varchar(12) NOT NULL CHECK (product_type IN ('PAINTING','FRAME')),
    name varchar(200) NOT NULL,
    price numeric(12,2) NOT NULL CHECK (price >= 0),
    stock_quantity integer NOT NULL CHECK (stock_quantity >= 0),
    image_url varchar(255),
    description varchar(500),
    PRIMARY KEY (product_id)
);

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

CREATE TABLE order_item (
    order_id varchar(20) NOT NULL,
    product_id varchar(20) NOT NULL,
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price numeric(12,2) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product (product_id)
);

-- SQL schema for Car Service and Booking System

DROP TABLE IF EXISTS mechanic_services;
DROP TABLE IF EXISTS feedback;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS time_slots;
DROP TABLE IF EXISTS services;
DROP TABLE IF EXISTS vehicles;
DROP TABLE IF EXISTS mechanics;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('ADMIN','CUSTOMER','MECHANIC') NOT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customers_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE mechanics (
    mechanic_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    specialization VARCHAR(100),
    is_active TINYINT(1) DEFAULT 1,
    join_date DATE,
    CONSTRAINT fk_mechanics_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE vehicles (
    vehicle_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    vehicle_number VARCHAR(20) NOT NULL UNIQUE,
    brand VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    fuel_type ENUM('PETROL','DIESEL','CNG','ELECTRIC') NOT NULL,
    manufacture_year INT,
    color VARCHAR(30),
    CONSTRAINT fk_vehicles_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE services (
    service_id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    description TEXT,
    base_price DECIMAL(10,2) NOT NULL,
    estimated_duration INT,
    is_active TINYINT(1) DEFAULT 1
);

CREATE TABLE time_slots (
    slot_id INT AUTO_INCREMENT PRIMARY KEY,
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    max_bookings INT NOT NULL
);

CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    vehicle_id INT NOT NULL,
    service_id INT NOT NULL,
    slot_id INT NOT NULL,
    assigned_mechanic_id INT,
    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    current_status ENUM('BOOKED','IN_PROGRESS','WAITING_FOR_PARTS','COMPLETED','DELIVERED','CANCELLED') NOT NULL DEFAULT 'BOOKED',
    remarks TEXT,
    CONSTRAINT fk_bookings_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_bookings_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    CONSTRAINT fk_bookings_service FOREIGN KEY (service_id) REFERENCES services(service_id),
    CONSTRAINT fk_bookings_slot FOREIGN KEY (slot_id) REFERENCES time_slots(slot_id),
    CONSTRAINT fk_bookings_mechanic FOREIGN KEY (assigned_mechanic_id) REFERENCES mechanics(mechanic_id)
);

CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_mode ENUM('CASH','CARD','UPI','ONLINE') NOT NULL,
    payment_status ENUM('PENDING','PAID','FAILED') NOT NULL,
    payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    transaction_ref VARCHAR(100),
    CONSTRAINT fk_payments_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);

CREATE TABLE feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    customer_id INT NOT NULL,
    rating INT NOT NULL,
    comments TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT fk_feedback_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    CONSTRAINT fk_feedback_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE mechanic_services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mechanic_id INT NOT NULL,
    service_id INT NOT NULL,
    CONSTRAINT fk_mechserv_mechanic FOREIGN KEY (mechanic_id) REFERENCES mechanics(mechanic_id),
    CONSTRAINT fk_mechserv_service FOREIGN KEY (service_id) REFERENCES services(service_id)
);

-- Default admin user (email: admin@example.com, password: admin123)
INSERT INTO users (email, password_hash, role)
VALUES ('admin@example.com', SHA2('admin123', 256), 'ADMIN');

DROP SCHEMA FLYTAU;
CREATE SCHEMA FLYTAU;
USE FLYTAU;


CREATE TABLE Guests (
    email VARCHAR(255) PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50)
);

CREATE TABLE Guest_Phones (
    email VARCHAR(255),
    phone_number VARCHAR(20),
    PRIMARY KEY (email, phone_number),
    FOREIGN KEY (email) REFERENCES Guests(email)
);

CREATE TABLE Registered (
    passport_number VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(255),
    birth_date DATE,
    registration_date DATE,
    password VARCHAR(50)
);

CREATE TABLE Registered_Phones (
    passport_number VARCHAR(50),
    phone_number VARCHAR(20),
    PRIMARY KEY (passport_number, phone_number),
    FOREIGN KEY (passport_number) REFERENCES Registered(passport_number)
);

create table planes (
    plane_id INT NOT NULL UNIQUE,
    size VARCHAR(45) NOT NULL,
    producer VARCHAR(45) NOT NULL,
    purchase_date DATE NOT NULL,
    primary key (plane_id)
);

CREATE TABLE route (
    origin VARCHAR(50) NOT NULL,
    destination VARCHAR(50) NOT NULL,
    minutes FLOAT,
    primary key (origin, destination)
);

CREATE TABLE Flights (
    flight_id INT NOT NULL AUTO_INCREMENT,
    departure_datetime DATETIME NOT NULL,
    origin VARCHAR(50) NOT NULL,
    destination VARCHAR(50) NOT NULL,
    flight_status varchar(45) NOT NULL,
    regular_price DECIMAL(10,2) NOT NULL,
    business_price DECIMAL(10,2) NOT NULL,
    plane_id INT NOT NULL,
    foreign key (plane_id) references planes(plane_id),
    foreign key (origin,destination) REFERENCES route(origin,destination),
    primary key (flight_id)
);

CREATE TABLE Orders (
    order_id INT PRIMARY KEY,
    order_status VARCHAR(50),
    total_amount DECIMAL(10,2),
    flight_id INT NOT NULL,
    order_date DATE,
    guest_email VARCHAR(255),
    registered_passport VARCHAR(50),
    FOREIGN KEY (guest_email) REFERENCES Guests(email),
    FOREIGN KEY (flight_id) references Flights(flight_id),
    FOREIGN KEY (registered_passport) REFERENCES Registered(passport_number),
    CHECK (
        (guest_email IS NOT NULL AND registered_passport IS NULL) OR
        (guest_email IS NULL AND registered_passport IS NOT NULL)
    )
);

create table plane_class (
    plane_id INT NOT NULL,
    class_type VARCHAR(45) NOT NULL,
    rows_number INT NOT NULL,
    columns_number INT NOT NULL,
    foreign key (plane_id) references planes(plane_id),
    primary key (plane_id, class_type)
);

CREATE TABLE Seats (
    plane_id INT NOT NULL,
    class_type VARCHAR(20) NOT NULL,
    seat_number VARCHAR(5) NOT NULL,
    rownumber INT NOT NULL,
    column_letter CHAR(1) NOT NULL,
    seat_status VARCHAR(20) NOT NULL DEFAULT 'OK',
    PRIMARY KEY (plane_id, class_type, seat_number),
    FOREIGN KEY (plane_id, class_type) REFERENCES Plane_Class(plane_id, class_type)
);

CREATE TABLE Booking_Seats (
    order_id INT,
    plane_id INT,
    class_type VARCHAR(20),
    seat_number VARCHAR(10),
    PRIMARY KEY (order_id, plane_id, class_type, seat_number),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (plane_id, class_type, seat_number) REFERENCES Seats(plane_id, class_type, seat_number)
);

CREATE TABLE FlightAttendants (
    attendant_id INT unique NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    city VARCHAR(50),
    street VARCHAR(50),
    house_number VARCHAR(10),
    start_date DATE NOT NULL,
    training_type VARCHAR(50) NOT NULL,
    primary key (attendant_id)
);

CREATE TABLE FlightAttendantPhones (
    attendant_id INT NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    FOREIGN KEY (attendant_id) REFERENCES FlightAttendants(attendant_id),
    primary key (attendant_id, phone_number)
);

CREATE TABLE Pilots (
    pilot_id INT unique NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    city VARCHAR(50),
    street VARCHAR(50),
    house_number VARCHAR(10),
    start_date DATE NOT NULL,
    training_type VARCHAR(50) NOT NULL,
    primary key (pilot_id)
);

CREATE TABLE PilotPhones (
    pilot_id INT NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    FOREIGN KEY (pilot_id) REFERENCES Pilots(pilot_id),
    primary key (pilot_id, phone_number)
);

CREATE TABLE Managers (
    manager_id INT unique NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    city VARCHAR(50),
    street VARCHAR(50),
    house_number VARCHAR(10),
    start_date DATE NOT NULL,
    password VARCHAR(255) NOT NULL,
    primary key (manager_id)
);

CREATE TABLE ManagerPhones (
    phone_id INT NOT NULL,
    manager_id INT NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    FOREIGN KEY (manager_id) REFERENCES Managers(manager_id),
    primary key (manager_id, phone_number)
);

CREATE TABLE FlightAttendantsFlights (
    flight_id INT NOT NULL,
    attendant_id INT NOT NULL,
    PRIMARY KEY (flight_id, attendant_id),
    FOREIGN KEY (flight_id) REFERENCES Flights(flight_id),
    FOREIGN KEY (attendant_id) REFERENCES FlightAttendants(attendant_id)
);

CREATE TABLE PilotsFlights (
    flight_id INT NOT NULL,
    pilot_id INT NOT NULL,
    PRIMARY KEY (flight_id, pilot_id),
    FOREIGN KEY (flight_id) REFERENCES Flights(flight_id),
    FOREIGN KEY (pilot_id) REFERENCES Pilots(pilot_id)
);

INSERT INTO Managers (
    manager_id, first_name, last_name, city, street, house_number, start_date, password
) VALUES (
    212987366, 'Hila', 'Cohen', 'Tel Aviv', 'Herzl', '10', '2022-01-01', '1234'
);

INSERT INTO route (origin, destination, minutes) VALUES ('Israel', 'New York', 600);

INSERT INTO planes (plane_id, size, producer, purchase_date) VALUES
    (1001, 'Large', 'Boeing', '2018-05-10'),
    (1002, 'Large', 'Airbus', '2019-07-15'),
    (2001, 'Small', 'Embraer', '2020-03-20'),
    (2002, 'Small', 'Bombardier', '2021-09-01');

-- =========================
-- Flight Attendants
-- =========================
INSERT INTO FlightAttendants (
    attendant_id, first_name, last_name, city, street, house_number, start_date, training_type
) VALUES
    (3001, 'Anna', 'Smith', 'Tel Aviv', 'Ben Yehuda', '12', '2020-01-01', 'long'),
    (3002, 'John', 'Brown', 'Haifa', 'Herzl', '5', '2019-03-15', 'long'),
    (3003, 'Emily', 'Davis', 'Jerusalem', 'King George', '8', '2021-06-10', 'short'),
    (3004, 'Michael', 'Wilson', 'Eilat', 'Palm', '22', '2018-11-20', 'long'),
    (3005, 'Sarah', 'Taylor', 'Tel Aviv', 'Allenby', '30', '2022-02-01', 'short');

-- =========================
-- Flight Attendant Phones
-- =========================
INSERT INTO FlightAttendantPhones (attendant_id, phone_number) VALUES
    (3001, '0501111111'),
    (3002, '0502222222'),
    (3003, '0503333333'),
    (3004, '0504444444'),
    (3005, '0505555555');

-- =========================
-- Pilots
-- =========================
INSERT INTO Pilots (
    pilot_id, first_name, last_name, city, street, house_number, start_date, training_type
) VALUES
    (4001, 'David', 'Miller', 'Tel Aviv', 'Dizengoff', '10', '2017-01-01', 'long'),
    (4002, 'Robert', 'Anderson', 'Haifa', 'Carmel', '3', '2016-05-20', 'long'),
    (4003, 'James', 'Thomas', 'Jerusalem', 'Jaffa', '14', '2019-09-01', 'long'),
    (4004, 'Daniel', 'Moore', 'Beer Sheva', 'Rager', '7', '2021-04-12', 'short');

-- =========================
-- Pilot Phones
-- =========================
INSERT INTO PilotPhones (pilot_id, phone_number) VALUES
    (4001, '0521111111'),
    (4002, '0522222222'),
    (4003, '0523333333'),
    (4004, '0524444444');

-- =========================
-- Plane Classes
-- =========================
INSERT INTO plane_class (plane_id, class_type, rows_number, columns_number) VALUES
    -- Large planes
    (1001, 'Business', 5, 4),
    (1001, 'Economy', 10, 6),
    (1002, 'Business', 5, 4),
    (1002, 'Economy', 10, 6),
    -- Small planes
    (2001, 'Business', 3, 4),
    (2001, 'Economy', 6, 4),
    (2002, 'Business', 3, 4),
    (2002, 'Economy', 6, 4);

-- =========================
-- Seats
-- =========================
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter, seat_status) VALUES
-- ======================
-- Plane 1001 (Large)
-- ======================
-- Business (rows 1–5, A–D)
(1001,'Business','1A',1,'A','OK'),
(1001,'Business','1B',1,'B','OK'),
(1001,'Business','1C',1,'C','OK'),
(1001,'Business','1D',1,'D','OK'),
(1001,'Business','2A',2,'A','OK'),
(1001,'Business','2B',2,'B','OK'),
(1001,'Business','2C',2,'C','OK'),
(1001,'Business','2D',2,'D','OK'),
(1001,'Business','3A',3,'A','OK'),
(1001,'Business','3B',3,'B','OK'),
(1001,'Business','3C',3,'C','OK'),
(1001,'Business','3D',3,'D','OK'),
(1001,'Business','4A',4,'A','OK'),
(1001,'Business','4B',4,'B','OK'),
(1001,'Business','4C',4,'C','OK'),
(1001,'Business','4D',4,'D','OK'),
(1001,'Business','5A',5,'A','OK'),
(1001,'Business','5B',5,'B','OK'),
(1001,'Business','5C',5,'C','OK'),
(1001,'Business','5D',5,'D','OK'),
-- Economy (rows 10–19, A–F)
(1001,'Economy','10A',10,'A','OK'),
(1001,'Economy','10B',10,'B','OK'),
(1001,'Economy','10C',10,'C','OK'),
(1001,'Economy','10D',10,'D','OK'),
(1001,'Economy','10E',10,'E','OK'),
(1001,'Economy','10F',10,'F','OK'),
(1001,'Economy','11A',11,'A','OK'),
(1001,'Economy','11B',11,'B','OK'),
(1001,'Economy','11C',11,'C','OK'),
(1001,'Economy','11D',11,'D','OK'),
(1001,'Economy','11E',11,'E','OK'),
(1001,'Economy','11F',11,'F','OK'),
-- ======================
-- Plane 1002 (Large)
-- ======================
-- Business
(1002,'Business','1A',1,'A','OK'),
(1002,'Business','1B',1,'B','OK'),
(1002,'Business','1C',1,'C','OK'),
(1002,'Business','1D',1,'D','OK'),
-- Economy
(1002,'Economy','10A',10,'A','OK'),
(1002,'Economy','10B',10,'B','OK'),
(1002,'Economy','10C',10,'C','OK'),
(1002,'Economy','10D',10,'D','OK'),
(1002,'Economy','10E',10,'E','OK'),
(1002,'Economy','10F',10,'F','OK'),
-- ======================
-- Plane 2001 (Small)
-- ======================
-- Business (rows 1–3, A–D)
(2001,'Business','1A',1,'A','OK'),
(2001,'Business','1B',1,'B','OK'),
(2001,'Business','1C',1,'C','OK'),
(2001,'Business','1D',1,'D','OK'),
(2001,'Business','2A',2,'A','OK'),
(2001,'Business','2B',2,'B','OK'),
(2001,'Business','2C',2,'C','OK'),
(2001,'Business','2D',2,'D','OK'),
(2001,'Business','3A',3,'A','OK'),
(2001,'Business','3B',3,'B','OK'),
(2001,'Business','3C',3,'C','OK'),
(2001,'Business','3D',3,'D','OK'),
-- Economy (rows 5–10, A–D)
(2001,'Economy','5A',5,'A','OK'),
(2001,'Economy','5B',5,'B','OK'),
(2001,'Economy','5C',5,'C','OK'),
(2001,'Economy','5D',5,'D','OK'),
-- ======================
-- Plane 2002 (Small)
-- ======================
-- Business
(2002,'Business','1A',1,'A','OK'),
(2002,'Business','1B',1,'B','OK'),
(2002,'Business','1C',1,'C','OK'),
(2002,'Business','1D',1,'D','OK'),
-- Economy
(2002,'Economy','5A',5,'A','OK'),
(2002,'Economy','5B',5,'B','OK'),
(2002,'Economy','5C',5,'C','OK'),
(2002,'Economy','5D',5,'D','OK');


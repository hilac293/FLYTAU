DROP SCHEMA IF EXISTS FLYTAU;
CREATE SCHEMA FLYTAU;
USE FLYTAU;

CREATE TABLE Guests (
    email VARCHAR(255) PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50));

CREATE TABLE Guest_Phones (
    email VARCHAR(255),
    phone_number VARCHAR(20),
    PRIMARY KEY (email, phone_number),
    FOREIGN KEY (email) REFERENCES Guests(email));


CREATE TABLE Registered (
    passport_number VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(255) UNIQUE,
    birth_date DATE,
    registration_date DATE,
    password VARCHAR(255));

CREATE TABLE Registered_Phones (
    passport_number VARCHAR(50),
    phone_number VARCHAR(20),
    PRIMARY KEY (passport_number, phone_number),
    FOREIGN KEY (passport_number) REFERENCES Registered(passport_number));

CREATE TABLE Planes (
    plane_id INT NOT NULL UNIQUE,
    size VARCHAR(45) NOT NULL,
    producer VARCHAR(45) NOT NULL,
    purchase_date DATE NOT NULL,
    PRIMARY KEY (plane_id));

CREATE TABLE Route (
    origin VARCHAR(50) NOT NULL,
    destination VARCHAR(50) NOT NULL,
    minutes FLOAT,
    PRIMARY KEY (origin, destination));

CREATE TABLE Flights (
    flight_id INT NOT NULL AUTO_INCREMENT,
    departure_datetime DATETIME NOT NULL,
    origin VARCHAR(50) NOT NULL,
    destination VARCHAR(50) NOT NULL,
    flight_status ENUM('Scheduled','Fully_Booked','Occurred','Cancelled') NOT NULL,
    regular_price DECIMAL(10,2) NOT NULL,
    business_price DECIMAL(10,2) NOT NULL,
    plane_id INT NOT NULL,
    FOREIGN KEY (plane_id) REFERENCES Planes(plane_id),
    FOREIGN KEY (origin, destination) REFERENCES Route(origin, destination),
    PRIMARY KEY (flight_id));


CREATE TABLE Orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    order_status ENUM(
        'ACTIVE',
        'COMPLETED',
        'CANCELLED_BY_CUSTOMER',
        'CANCELLED_BY_SYSTEM') NOT NULL,
    total_amount DECIMAL(10,2),
    flight_id INT NOT NULL,
    order_date DATE,
    guest_email VARCHAR(255) NULL,
    registered_email VARCHAR(255) NULL,
    FOREIGN KEY (flight_id) REFERENCES Flights(flight_id),
    FOREIGN KEY (guest_email) REFERENCES Guests(email)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    FOREIGN KEY (registered_email) REFERENCES Registered(email)
        ON DELETE SET NULL
        ON UPDATE CASCADE);

CREATE TABLE Plane_Class (
    plane_id INT NOT NULL,
    class_type VARCHAR(45) NOT NULL,
    rows_number INT NOT NULL,
    columns_number INT NOT NULL,
    PRIMARY KEY (plane_id, class_type),
    FOREIGN KEY (plane_id) REFERENCES Planes(plane_id));

CREATE TABLE Seats (
    plane_id INT NOT NULL,
    class_type VARCHAR(20) NOT NULL,
    seat_number VARCHAR(5) NOT NULL,
    rownumber INT NOT NULL,
    column_letter CHAR(1) NOT NULL,
    PRIMARY KEY (plane_id, class_type, seat_number),
    FOREIGN KEY (plane_id, class_type)
        REFERENCES Plane_Class(plane_id, class_type));

CREATE TABLE Booking_Seats (
    order_id INT,
    plane_id INT,
    class_type VARCHAR(20),
    seat_number VARCHAR(10),
    PRIMARY KEY (order_id, plane_id, class_type, seat_number),
    FOREIGN KEY (order_id) REFERENCES Orders(order_id),
    FOREIGN KEY (plane_id, class_type, seat_number)
        REFERENCES Seats(plane_id, class_type, seat_number));

CREATE TABLE FlightAttendants (
    attendant_id INT NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    city VARCHAR(50),
    street VARCHAR(50),
    house_number VARCHAR(10),
    start_date DATE NOT NULL,
    training_type VARCHAR(50) NOT NULL,
    PRIMARY KEY (attendant_id));

CREATE TABLE FlightAttendantPhones (
    attendant_id INT NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    PRIMARY KEY (attendant_id, phone_number),
    FOREIGN KEY (attendant_id) REFERENCES FlightAttendants(attendant_id));

CREATE TABLE Pilots (
    pilot_id INT NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    city VARCHAR(50),
    street VARCHAR(50),
    house_number VARCHAR(10),
    start_date DATE NOT NULL,
    training_type VARCHAR(50) NOT NULL,
    PRIMARY KEY (pilot_id));

CREATE TABLE PilotPhones (
    pilot_id INT NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    PRIMARY KEY (pilot_id, phone_number),
    FOREIGN KEY (pilot_id) REFERENCES Pilots(pilot_id));

CREATE TABLE Managers (
    manager_id INT NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    city VARCHAR(50),
    street VARCHAR(50),
    house_number VARCHAR(10),
    start_date DATE NOT NULL,
    password VARCHAR(255) NOT NULL,
    PRIMARY KEY (manager_id));

CREATE TABLE ManagerPhones (
    manager_id INT NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    PRIMARY KEY (manager_id, phone_number),
    FOREIGN KEY (manager_id) REFERENCES Managers(manager_id));


CREATE TABLE FlightAttendantsFlights (
    flight_id INT NOT NULL,
    attendant_id INT NOT NULL,
    PRIMARY KEY (flight_id, attendant_id),
    FOREIGN KEY (flight_id) REFERENCES Flights(flight_id),
    FOREIGN KEY (attendant_id) REFERENCES FlightAttendants(attendant_id));

CREATE TABLE PilotsFlights (
    flight_id INT NOT NULL,
    pilot_id INT NOT NULL,
    PRIMARY KEY (flight_id, pilot_id),
    FOREIGN KEY (flight_id) REFERENCES Flights(flight_id),
    FOREIGN KEY (pilot_id) REFERENCES Pilots(pilot_id));


-- =========================
-- Managers
-- =========================
INSERT INTO Managers (
    manager_id, first_name, last_name, city, street, house_number, start_date, password
) VALUES (
    212987366, 'Hila', 'Cohen', 'Tel Aviv', 'Herzl', '10', '2022-01-01', '1234'
);
INSERT INTO Managers (
    manager_id, first_name, last_name, city, street, house_number, start_date, password
) VALUES (
    212987367, 'Yossi', 'Levi', 'Haifa', 'Hertzel', '15', '2022-02-01', '5678'
);

-- =========================
-- Routes
-- =========================
INSERT INTO Route (origin, destination, minutes) VALUES
('תל אביב - נתב״ג', 'ניו יורק', 600),
('תל אביב - נתב״ג', 'לונדון', 360),
('תל אביב - נתב״ג', 'פריז', 400),
('אילת', 'לונדון', 420),
('אילת', 'פריז', 450),
('ניו יורק', 'תל אביב - נתב״ג', 600),
('לונדון', 'תל אביב - נתב״ג', 360),
('פריז', 'תל אביב - נתב״ג', 400),
('לונדון', 'אילת', 420),
('פריז', 'אילת', 450);

-- =========================
-- Planes
-- =========================
INSERT INTO Planes (plane_id, size, producer, purchase_date) VALUES
    (1001, 'Large', 'Boeing', '2018-05-10'),
    (1002, 'Large', 'Airbus', '2019-07-15'),
    (2001, 'Small', 'Boeing', '2020-03-20'),
    (2002, 'Small', 'Airbus', '2021-09-01'),
    (2003, 'Small', 'Dassault', '2022-04-10'),
    (2004, 'Small', 'Dassault', '2022-08-05');


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

INSERT INTO FlightAttendants (
    attendant_id, first_name, last_name, city, street, house_number, start_date, training_type
) VALUES
(3006, 'Olivia', 'Martinez', 'Tel Aviv', 'Allenby', '32', '2020-07-01', 'long'),
(3007, 'Sophia', 'Hernandez', 'Haifa', 'Carmel', '4', '2019-09-10', 'long'),
(3008, 'Isabella', 'Lopez', 'Jerusalem', 'King George', '9', '2021-05-20', 'short'),
(3009, 'Mia', 'Gonzalez', 'Eilat', 'Hayam', '7', '2018-08-15', 'long'),
(3010, 'Amelia', 'Perez', 'Tel Aviv', 'Dizengoff', '11', '2022-01-05', 'short'),
(3011, 'Harper', 'Robinson', 'Haifa', 'Herzl', '3', '2019-03-18', 'long'),
(3012, 'Evelyn', 'Clark', 'Jerusalem', 'Jaffa', '12', '2021-06-25', 'short'),
(3013, 'Abigail', 'Rodriguez', 'Eilat', 'Palm', '14', '2018-11-30', 'long'),
(3014, 'Ella', 'Lewis', 'Tel Aviv', 'Ben Yehuda', '16', '2020-12-01', 'short'),
(3015, 'Avery', 'Walker', 'Haifa', 'Hertzel', '7', '2021-02-10', 'long'),
(3016, 'Scarlett', 'Hall', 'Jerusalem', 'King George', '5', '2022-03-12', 'short'),
(3017, 'Grace', 'Allen', 'Eilat', 'Rager', '9', '2019-07-08', 'long'),
(3018, 'Chloe', 'Young', 'Tel Aviv', 'Ahad Haam', '6', '2021-09-15', 'short'),
(3019, 'Victoria', 'Hernandez', 'Haifa', 'Carmel', '8', '2020-10-10', 'long'),
(3020, 'Lillian', 'King', 'Jerusalem', 'Ben Yehuda', '10', '2022-05-01', 'short');

-- =========================
-- Flight Attendant Phones
-- =========================
INSERT INTO FlightAttendantPhones (attendant_id, phone_number) VALUES
    (3001, '0501111111'),
    (3002, '0502222222'),
    (3003, '0503333333'),
    (3004, '0504444444'),
    (3005, '0505555555');

INSERT INTO FlightAttendantPhones (attendant_id, phone_number) VALUES
(3006, '0506661111'),
(3007, '0506662222'),
(3008, '0506663333'),
(3009, '0506664444'),
(3010, '0506665555'),
(3011, '0506666666'),
(3012, '0506667777'),
(3013, '0506668888'),
(3014, '0506669999'),
(3015, '0506670000'),
(3016, '0506671111'),
(3017, '0506672222'),
(3018, '0506673333'),
(3019, '0506674444'),
(3020, '0506675555');

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

INSERT INTO Pilots (
    pilot_id, first_name, last_name, city, street, house_number, start_date, training_type
) VALUES
(4005, 'Ethan', 'Hall', 'Tel Aviv', 'Rothschild', '12', '2018-05-01', 'long'),
(4006, 'Liam', 'Young', 'Haifa', 'Hatzionut', '8', '2017-08-12', 'long'),
(4007, 'Noah', 'King', 'Jerusalem', 'Ben Yehuda', '20', '2019-10-15', 'long'),
(4008, 'Mason', 'Wright', 'Beer Sheva', 'Hagalil', '11', '2020-03-22', 'short'),
(4009, 'Logan', 'Scott', 'Eilat', 'Hayam', '5', '2021-06-10', 'short'),
(4010, 'Lucas', 'Adams', 'Tel Aviv', 'Ahad Haam', '9', '2016-12-01', 'long');

-- =========================
-- Pilot Phones
-- =========================
INSERT INTO PilotPhones (pilot_id, phone_number) VALUES
    (4001, '0521111111'),
    (4002, '0522222222'),
    (4003, '0523333333'),
    (4004, '0524444444');

INSERT INTO PilotPhones (pilot_id, phone_number) VALUES
(4005, '0525551111'),
(4006, '0525552222'),
(4007, '0525553333'),
(4008, '0525554444'),
(4009, '0525555555'),
(4010, '0525556666');

-- =========================
-- Plane Classes
-- =========================
INSERT INTO Plane_Class (plane_id, class_type, rows_number, columns_number) VALUES
    -- Large planes
    (1001, 'Business', 5, 4),
    (1001, 'Economy', 10, 6),
    (1002, 'Business', 5, 4),
    (1002, 'Economy', 10, 6),
    -- Small planes
    (2001, 'Business', 3, 4),
    (2001, 'Economy', 6, 4),
    (2002, 'Business', 3, 4),
    (2002, 'Economy', 6, 4),
    (2003, 'Business', 3, 4),
    (2003, 'Economy', 6, 4),
    (2004, 'Business', 3, 4),
    (2004, 'Economy', 6, 4);


-- =========================
-- Seats
-- =========================
-- =========================
-- =========================
-- Seats for Plane 1001 (Large)
-- Business 5x4 = 20 seats
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(1001,'Business','1A',1,'A'),(1001,'Business','1B',1,'B'),(1001,'Business','1C',1,'C'),(1001,'Business','1D',1,'D'),
(1001,'Business','2A',2,'A'),(1001,'Business','2B',2,'B'),(1001,'Business','2C',2,'C'),(1001,'Business','2D',2,'D'),
(1001,'Business','3A',3,'A'),(1001,'Business','3B',3,'B'),(1001,'Business','3C',3,'C'),(1001,'Business','3D',3,'D'),
(1001,'Business','4A',4,'A'),(1001,'Business','4B',4,'B'),(1001,'Business','4C',4,'C'),(1001,'Business','4D',4,'D'),
(1001,'Business','5A',5,'A'),(1001,'Business','5B',5,'B'),(1001,'Business','5C',5,'C'),(1001,'Business','5D',5,'D');

-- Economy 10x6 = 60 seats (שורות 6-15)
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(1001,'Economy','6A',6,'A'),(1001,'Economy','6B',6,'B'),(1001,'Economy','6C',6,'C'),(1001,'Economy','6D',6,'D'),(1001,'Economy','6E',6,'E'),(1001,'Economy','6F',6,'F'),
(1001,'Economy','7A',7,'A'),(1001,'Economy','7B',7,'B'),(1001,'Economy','7C',7,'C'),(1001,'Economy','7D',7,'D'),(1001,'Economy','7E',7,'E'),(1001,'Economy','7F',7,'F'),
(1001,'Economy','8A',8,'A'),(1001,'Economy','8B',8,'B'),(1001,'Economy','8C',8,'C'),(1001,'Economy','8D',8,'D'),(1001,'Economy','8E',8,'E'),(1001,'Economy','8F',8,'F'),
(1001,'Economy','9A',9,'A'),(1001,'Economy','9B',9,'B'),(1001,'Economy','9C',9,'C'),(1001,'Economy','9D',9,'D'),(1001,'Economy','9E',9,'E'),(1001,'Economy','9F',9,'F'),
(1001,'Economy','10A',10,'A'),(1001,'Economy','10B',10,'B'),(1001,'Economy','10C',10,'C'),(1001,'Economy','10D',10,'D'),(1001,'Economy','10E',10,'E'),(1001,'Economy','10F',10,'F'),
(1001,'Economy','11A',11,'A'),(1001,'Economy','11B',11,'B'),(1001,'Economy','11C',11,'C'),(1001,'Economy','11D',11,'D'),(1001,'Economy','11E',11,'E'),(1001,'Economy','11F',11,'F'),
(1001,'Economy','12A',12,'A'),(1001,'Economy','12B',12,'B'),(1001,'Economy','12C',12,'C'),(1001,'Economy','12D',12,'D'),(1001,'Economy','12E',12,'E'),(1001,'Economy','12F',12,'F'),
(1001,'Economy','13A',13,'A'),(1001,'Economy','13B',13,'B'),(1001,'Economy','13C',13,'C'),(1001,'Economy','13D',13,'D'),(1001,'Economy','13E',13,'E'),(1001,'Economy','13F',13,'F'),
(1001,'Economy','14A',14,'A'),(1001,'Economy','14B',14,'B'),(1001,'Economy','14C',14,'C'),(1001,'Economy','14D',14,'D'),(1001,'Economy','14E',14,'E'),(1001,'Economy','14F',14,'F'),
(1001,'Economy','15A',15,'A'),(1001,'Economy','15B',15,'B'),(1001,'Economy','15C',15,'C'),(1001,'Economy','15D',15,'D'),(1001,'Economy','15E',15,'E'),(1001,'Economy','15F',15,'F');

-- =========================
-- Seats for Plane 1002 (Large)
-- Business 5x4 = 20 seats
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(1002,'Business','1A',1,'A'),(1002,'Business','1B',1,'B'),(1002,'Business','1C',1,'C'),(1002,'Business','1D',1,'D'),
(1002,'Business','2A',2,'A'),(1002,'Business','2B',2,'B'),(1002,'Business','2C',2,'C'),(1002,'Business','2D',2,'D'),
(1002,'Business','3A',3,'A'),(1002,'Business','3B',3,'B'),(1002,'Business','3C',3,'C'),(1002,'Business','3D',3,'D'),
(1002,'Business','4A',4,'A'),(1002,'Business','4B',4,'B'),(1002,'Business','4C',4,'C'),(1002,'Business','4D',4,'D'),
(1002,'Business','5A',5,'A'),(1002,'Business','5B',5,'B'),(1002,'Business','5C',5,'C'),(1002,'Business','5D',5,'D');

-- Economy 10x6 = 60 seats (שורות 6-15)
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(1002,'Economy','6A',6,'A'),(1002,'Economy','6B',6,'B'),(1002,'Economy','6C',6,'C'),(1002,'Economy','6D',6,'D'),(1002,'Economy','6E',6,'E'),(1002,'Economy','6F',6,'F'),
(1002,'Economy','7A',7,'A'),(1002,'Economy','7B',7,'B'),(1002,'Economy','7C',7,'C'),(1002,'Economy','7D',7,'D'),(1002,'Economy','7E',7,'E'),(1002,'Economy','7F',7,'F'),
(1002,'Economy','8A',8,'A'),(1002,'Economy','8B',8,'B'),(1002,'Economy','8C',8,'C'),(1002,'Economy','8D',8,'D'),(1002,'Economy','8E',8,'E'),(1002,'Economy','8F',8,'F'),
(1002,'Economy','9A',9,'A'),(1002,'Economy','9B',9,'B'),(1002,'Economy','9C',9,'C'),(1002,'Economy','9D',9,'D'),(1002,'Economy','9E',9,'E'),(1002,'Economy','9F',9,'F'),
(1002,'Economy','10A',10,'A'),(1002,'Economy','10B',10,'B'),(1002,'Economy','10C',10,'C'),(1002,'Economy','10D',10,'D'),(1002,'Economy','10E',10,'E'),(1002,'Economy','10F',10,'F'),
(1002,'Economy','11A',11,'A'),(1002,'Economy','11B',11,'B'),(1002,'Economy','11C',11,'C'),(1002,'Economy','11D',11,'D'),(1002,'Economy','11E',11,'E'),(1002,'Economy','11F',11,'F'),
(1002,'Economy','12A',12,'A'),(1002,'Economy','12B',12,'B'),(1002,'Economy','12C',12,'C'),(1002,'Economy','12D',12,'D'),(1002,'Economy','12E',12,'E'),(1002,'Economy','12F',12,'F'),
(1002,'Economy','13A',13,'A'),(1002,'Economy','13B',13,'B'),(1002,'Economy','13C',13,'C'),(1002,'Economy','13D',13,'D'),(1002,'Economy','13E',13,'E'),(1002,'Economy','13F',13,'F'),
(1002,'Economy','14A',14,'A'),(1002,'Economy','14B',14,'B'),(1002,'Economy','14C',14,'C'),(1002,'Economy','14D',14,'D'),(1002,'Economy','14E',14,'E'),(1002,'Economy','14F',14,'F'),
(1002,'Economy','15A',15,'A'),(1002,'Economy','15B',15,'B'),(1002,'Economy','15C',15,'C'),(1002,'Economy','15D',15,'D'),(1002,'Economy','15E',15,'E'),(1002,'Economy','15F',15,'F');

-- =========================
-- Seats for Plane 2001 (Small)
-- Business 4x4 = 16 seats
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(2001,'Business','1A',1,'A'),(2001,'Business','1B',1,'B'),(2001,'Business','1C',1,'C'),(2001,'Business','1D',1,'D'),
(2001,'Business','2A',2,'A'),(2001,'Business','2B',2,'B'),(2001,'Business','2C',2,'C'),(2001,'Business','2D',2,'D'),
(2001,'Business','3A',3,'A'),(2001,'Business','3B',3,'B'),(2001,'Business','3C',3,'C'),(2001,'Business','3D',3,'D'),
(2001,'Business','4A',4,'A'),(2001,'Business','4B',4,'B'),(2001,'Business','4C',4,'C'),(2001,'Business','4D',4,'D');

-- Economy 6x4 = 24 seats (שורות 5-10)
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(2001,'Economy','5A',5,'A'),(2001,'Economy','5B',5,'B'),(2001,'Economy','5C',5,'C'),(2001,'Economy','5D',5,'D'),
(2001,'Economy','6A',6,'A'),(2001,'Economy','6B',6,'B'),(2001,'Economy','6C',6,'C'),(2001,'Economy','6D',6,'D'),
(2001,'Economy','7A',7,'A'),(2001,'Economy','7B',7,'B'),(2001,'Economy','7C',7,'C'),(2001,'Economy','7D',7,'D'),
(2001,'Economy','8A',8,'A'),(2001,'Economy','8B',8,'B'),(2001,'Economy','8C',8,'C'),(2001,'Economy','8D',8,'D'),
(2001,'Economy','9A',9,'A'),(2001,'Economy','9B',9,'B'),(2001,'Economy','9C',9,'C'),(2001,'Economy','9D',9,'D'),
(2001,'Economy','10A',10,'A'),(2001,'Economy','10B',10,'B'),(2001,'Economy','10C',10,'C'),(2001,'Economy','10D',10,'D');

-- =========================
-- Seats for Plane 2002 (Small)
-- Business 4x4 = 16 seats
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(2002,'Business','1A',1,'A'),(2002,'Business','1B',1,'B'),(2002,'Business','1C',1,'C'),(2002,'Business','1D',1,'D'),
(2002,'Business','2A',2,'A'),(2002,'Business','2B',2,'B'),(2002,'Business','2C',2,'C'),(2002,'Business','2D',2,'D'),
(2002,'Business','3A',3,'A'),(2002,'Business','3B',3,'B'),(2002,'Business','3C',3,'C'),(2002,'Business','3D',3,'D'),
(2002,'Business','4A',4,'A'),(2002,'Business','4B',4,'B'),(2002,'Business','4C',4,'C'),(2002,'Business','4D',4,'D');

-- Economy 6x4 = 24 seats (שורות 5-10)
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(2002,'Economy','5A',5,'A'),(2002,'Economy','5B',5,'B'),(2002,'Economy','5C',5,'C'),(2002,'Economy','5D',5,'D'),
(2002,'Economy','6A',6,'A'),(2002,'Economy','6B',6,'B'),(2002,'Economy','6C',6,'C'),(2002,'Economy','6D',6,'D'),
(2002,'Economy','7A',7,'A'),(2002,'Economy','7B',7,'B'),(2002,'Economy','7C',7,'C'),(2002,'Economy','7D',7,'D'),
(2002,'Economy','8A',8,'A'),(2002,'Economy','8B',8,'B'),(2002,'Economy','8C',8,'C'),(2002,'Economy','8D',8,'D'),
(2002,'Economy','9A',9,'A'),(2002,'Economy','9B',9,'B'),(2002,'Economy','9C',9,'C'),(2002,'Economy','9D',9,'D'),
(2002,'Economy','10A',10,'A'),(2002,'Economy','10B',10,'B'),(2002,'Economy','10C',10,'C'),(2002,'Economy','10D',10,'D');

-- =========================
-- Seats for Plane 2003 (Small)
-- Business 4x4 = 16 seats
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(2003,'Business','1A',1,'A'),(2003,'Business','1B',1,'B'),(2003,'Business','1C',1,'C'),(2003,'Business','1D',1,'D'),
(2003,'Business','2A',2,'A'),(2003,'Business','2B',2,'B'),(2003,'Business','2C',2,'C'),(2003,'Business','2D',2,'D'),
(2003,'Business','3A',3,'A'),(2003,'Business','3B',3,'B'),(2003,'Business','3C',3,'C'),(2003,'Business','3D',3,'D'),
(2003,'Business','4A',4,'A'),(2003,'Business','4B',4,'B'),(2003,'Business','4C',4,'C'),(2003,'Business','4D',4,'D');

-- Economy 6x4 = 24 seats (שורות 5-10)
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(2003,'Economy','5A',5,'A'),(2003,'Economy','5B',5,'B'),(2003,'Economy','5C',5,'C'),(2003,'Economy','5D',5,'D'),
(2003,'Economy','6A',6,'A'),(2003,'Economy','6B',6,'B'),(2003,'Economy','6C',6,'C'),(2003,'Economy','6D',6,'D'),
(2003,'Economy','7A',7,'A'),(2003,'Economy','7B',7,'B'),(2003,'Economy','7C',7,'C'),(2003,'Economy','7D',7,'D'),
(2003,'Economy','8A',8,'A'),(2003,'Economy','8B',8,'B'),(2003,'Economy','8C',8,'C'),(2003,'Economy','8D',8,'D'),
(2003,'Economy','9A',9,'A'),(2003,'Economy','9B',9,'B'),(2003,'Economy','9C',9,'C'),(2003,'Economy','9D',9,'D'),
(2003,'Economy','10A',10,'A'),(2003,'Economy','10B',10,'B'),(2003,'Economy','10C',10,'C'),(2003,'Economy','10D',10,'D');

-- =========================
-- Seats for Plane 2004 (Small)
-- Business 4x4 = 16 seats
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(2004,'Business','1A',1,'A'),(2004,'Business','1B',1,'B'),(2004,'Business','1C',1,'C'),(2004,'Business','1D',1,'D'),
(2004,'Business','2A',2,'A'),(2004,'Business','2B',2,'B'),(2004,'Business','2C',2,'C'),(2004,'Business','2D',2,'D'),
(2004,'Business','3A',3,'A'),(2004,'Business','3B',3,'B'),(2004,'Business','3C',3,'C'),(2004,'Business','3D',3,'D'),
(2004,'Business','4A',4,'A'),(2004,'Business','4B',4,'B'),(2004,'Business','4C',4,'C'),(2004,'Business','4D',4,'D');

-- Economy 6x4 = 24 seats (שורות 5-10)
INSERT INTO Seats (plane_id, class_type, seat_number, rownumber, column_letter) VALUES
(2004,'Economy','5A',5,'A'),(2004,'Economy','5B',5,'B'),(2004,'Economy','5C',5,'C'),(2004,'Economy','5D',5,'D'),
(2004,'Economy','6A',6,'A'),(2004,'Economy','6B',6,'B'),(2004,'Economy','6C',6,'C'),(2004,'Economy','6D',6,'D'),
(2004,'Economy','7A',7,'A'),(2004,'Economy','7B',7,'B'),(2004,'Economy','7C',7,'C'),(2004,'Economy','7D',7,'D'),
(2004,'Economy','8A',8,'A'),(2004,'Economy','8B',8,'B'),(2004,'Economy','8C',8,'C'),(2004,'Economy','8D',8,'D'),
(2004,'Economy','9A',9,'A'),(2004,'Economy','9B',9,'B'),(2004,'Economy','9C',9,'C'),(2004,'Economy','9D',9,'D'),
(2004,'Economy','10A',10,'A'),(2004,'Economy','10B',10,'B'),(2004,'Economy','10C',10,'C'),(2004,'Economy','10D',10,'D');

-- =========================
-- Flights (פעילות / לא פעילות)
-- =========================
INSERT INTO Flights 
(departure_datetime, origin, destination, flight_status, regular_price, business_price, plane_id)
VALUES
-- טיסות פעילות (Scheduled)
('2026-03-06 07:00:00', 'תל אביב - נתב״ג', 'לונדון', 'Scheduled', 1200.00, 2000.00, 2001),
('2026-03-06 19:00:00', 'תל אביב - נתב״ג', 'לונדון', 'Scheduled', 1250.00, 2100.00, 2002),
('2026-03-07 09:00:00', 'תל אביב - נתב״ג', 'פריז', 'Scheduled', 1100.00, 1900.00, 1001),
('2026-03-07 17:00:00', 'תל אביב - נתב״ג', 'פריז', 'Scheduled', 1150.00, 1950.00, 1002),
('2026-03-08 08:00:00', 'תל אביב - נתב״ג', 'ניו יורק', 'Scheduled', 1500.00, 2500.00, 1001),
('2026-03-08 22:00:00', 'תל אביב - נתב״ג', 'ניו יורק', 'Scheduled', 1550.00, 2600.00, 1002),

-- טיסות לא פעילות (Cancelled)
('2026-02-20 10:00:00', 'אילת', 'לונדון', 'Cancelled', 1300.00, 2200.00, 2001),
('2026-02-22 15:00:00', 'אילת', 'פריז', 'Cancelled', 1250.00, 2150.00, 2002),
('2026-02-25 12:00:00', 'לונדון', 'תל אביב - נתב״ג', 'Cancelled', 1200.00, 2000.00, 2001),
('2026-02-28 18:00:00', 'פריז', 'תל אביב - נתב״ג', 'Cancelled', 1180.00, 1980.00, 2002);

-- =========================
-- Registered Users
-- =========================
INSERT INTO Registered (passport_number, first_name, last_name, email, birth_date, registration_date, password) VALUES
('P123456', 'Daniel', 'Mizrahi', 'daniel@example.com', '1990-06-15', '2023-01-01', 'regpass1'),
('P654321', 'Tamar', 'Levi', 'tamar@example.com', '1988-12-20', '2023-02-10', 'regpass2');

INSERT INTO Registered_Phones (passport_number, phone_number) VALUES
('P123456', '0520001111'),
('P123456', '0520002222'),
('P654321', '0520003333');

-- =========================
-- Guests
-- =========================
INSERT INTO Guests (email, first_name, last_name) VALUES
('guest1@example.com', 'John', 'Doe'),
('guest2@example.com', 'Jane', 'Smith');

INSERT INTO Guest_Phones (email, phone_number) VALUES
('guest1@example.com', '0501111111'),
('guest2@example.com', '0502222222');

-- =========================
-- Orders
-- =========================
INSERT INTO Orders (order_status, total_amount, flight_id, order_date, guest_email, registered_email) VALUES
('ACTIVE', 1200.00, 1, '2026-01-15', NULL, 'daniel@example.com'),
('COMPLETED', 2500.00, 5, '2026-01-10', 'guest1@example.com', NULL),
('CANCELLED_BY_CUSTOMER', 1150.00, 4, '2026-01-12', NULL, 'tamar@example.com'),
('ACTIVE', 1550.00, 6, '2026-01-16', 'guest2@example.com', NULL);

-- =========================
-- Booking Seats
-- =========================
INSERT INTO Booking_Seats (order_id, plane_id, class_type, seat_number) VALUES
(1, 2001, 'Business', '1A'),
(1, 2001, 'Business', '1B'),
(2, 1001, 'Economy', '10A'),
(3, 1002, 'Business', '1C'),
(4, 1002, 'Economy', '10D');

-- =========================
-- Assign Flight Attendants to Flights
-- =========================
INSERT INTO FlightAttendantsFlights (flight_id, attendant_id) VALUES
(1, 3001),
(1, 3002),
(2, 3003),
(2, 3004),
(3, 3001),
(3, 3005),
(4, 3002),
(5, 3003),
(6, 3004);

-- =========================
-- Assign Pilots to Flights
-- =========================
INSERT INTO PilotsFlights (flight_id, pilot_id) VALUES
(1, 4001),
(2, 4002),
(3, 4003),
(4, 4004),
(5, 4001),
(6, 4002);


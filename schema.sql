CREATE DATABASE IF NOT EXISTS comp440;
USE comp440;

CREATE TABLE IF NOT EXISTS `user` (
    username  VARCHAR(50)  PRIMARY KEY,
    password  VARCHAR(255) NOT NULL,          
    firstName VARCHAR(50)  NOT NULL,
    lastName  VARCHAR(50)  NOT NULL,
    email     VARCHAR(100) NOT NULL UNIQUE,
    phone     VARCHAR(20)  NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS `item` (
    itemID INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL (10,2) NOT NULL CHECK (price >= 0),
    datePosted DATE NOT NULL,
    username VARCHAR(50) NOT NULL, 
    FOREIGN KEY (username) REFERENCES `user`(username) ON DELETE CASCADE
);
    
CREATE TABLE IF NOT EXISTS 	`review` (
    reviewID INT AUTO_INCREMENT PRIMARY KEY,
    rating ENUM('Excellent','Good','Fair','Poor') NOT NULL,
    comment VARCHAR(300) NOT NULL,
    reviewDate DATE NOT NULL,
    itemID INT NOT NULL,
    username VARCHAR(50) NOT NULL,
    FOREIGN KEY (itemID) REFERENCES `item`(itemID) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES `user`(username) ON DELETE CASCADE,
    UNIQUE (username, itemID)
);

CREATE TABLE IF NOT EXISTS `category` (
    categoryName VARCHAR(35) NOT NULL,
    itemID INT NOT NULL,
    PRIMARY KEY (categoryName, itemID),
    FOREIGN KEY (itemID) REFERENCES `item`(itemID) ON DELETE CASCADE,
    CHECK (REGEXP_LIKE(categoryName, '^[a-z]+$', 'c') = 1)
);

DROP TRIGGER IF EXISTS limit_items_per_day;




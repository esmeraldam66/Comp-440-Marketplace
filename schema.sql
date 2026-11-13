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

DROP PROCEDURE IF EXISTS add_item;
DELIMITER //
CREATE PROCEDURE add_item(
    IN p_title VARCHAR(100),
    IN p_description TEXT,
    IN p_price DECIMAL (10,2),
    IN p_username VARCHAR(50), 
    OUT p_itemID INT
)
BEGIN
	IF (SELECT COUNT(*) FROM item
		WHERE username = p_username AND datePosted = curdate()) >= 2 THEN
        SIGNAL SQLSTATE '45000'
			SET MESSAGE_TEXT = 'You may only post 2 items per day.';
	ELSE
		INSERT INTO item (title, description, price, datePosted, username)
        VALUES (p_title, p_description, p_price, curdate(), p_username);
		SET p_itemID = LAST_INSERT_ID();
    END IF;
END//
DELIMITER ;

DROP PROCEDURE IF EXISTS add_review;
DELIMITER //
CREATE PROCEDURE add_review(
    IN p_rating VARCHAR(10),
    IN p_comment VARCHAR(300),
    IN p_itemID INT,
    IN p_username VARCHAR(50)
)
BEGIN
	IF p_username = (SELECT username FROM item WHERE itemID = p_itemID) THEN
		SIGNAL SQLSTATE '45000'
			SET MESSAGE_TEXT = 'You cannot review your own item.';
    
    ELSEIF (SELECT COUNT(*) FROM review
		WHERE username = p_username AND reviewDate = curdate()) >= 2 THEN
        SIGNAL SQLSTATE '45000'
			SET MESSAGE_TEXT = 'You may only review 2 items per day.';
	ELSE
		INSERT INTO review (rating, comment, reviewDate, itemID, username)
        VALUES (p_rating, p_comment, curdate(), p_itemID, p_username);
    END IF;
END//
DELIMITER ;
	
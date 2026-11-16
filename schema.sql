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

DROP TRIGGER IF EXISTS no_review_modification;
DELIMITER //
CREATE TRIGGER no_review_modification
BEFORE UPDATE ON review
FOR EACH ROW
BEGIN
	SIGNAL SQLSTATE '45000'
			SET MESSAGE_TEXT = 'You may not modify your review.';
END//
DELIMITER ;

CREATE TABLE IF NOT EXISTS daily_posts (
    username VARCHAR(50) NOT NULL,
    postDate DATE NOT NULL,
    postCount INT NOT NULL DEFAULT 0,
    PRIMARY KEY (username, postDate),
    FOREIGN KEY (username) REFERENCES `user`(username)
        ON DELETE CASCADE,
    CHECK (postCount BETWEEN 0 AND 2)
);

INSERT INTO daily_posts (username, postDate, postCount)
SELECT username, datePosted, COUNT(*)
FROM item
GROUP BY username, datePosted;

DROP TRIGGER IF EXISTS limit_daily_posts;

DELIMITER //

CREATE TRIGGER limit_daily_posts
BEFORE INSERT ON item
FOR EACH ROW
BEGIN
    SET NEW.datePosted = CURDATE();

    INSERT INTO daily_posts (username, postDate, postCount)
    VALUES (NEW.username, CURDATE(), 0)
    ON DUPLICATE KEY UPDATE postCount = postCount;

    UPDATE daily_posts
    SET postCount = postCount + 1
    WHERE username = NEW.username
      AND postDate = CURDATE()
      AND postCount < 2;

    IF ROW_COUNT() = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'You may only post 2 items per day.';
    END IF;
END//

DELIMITER ;
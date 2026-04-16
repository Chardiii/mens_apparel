/*
SQLyog Ultimate v10.00 Beta1
MySQL - 5.5.5-10.4.32-MariaDB : Database - ecommerce_db
*********************************************************************
*/

/*!40101 SET NAMES utf8 */;

/*!40101 SET SQL_MODE=''*/;

/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
CREATE DATABASE /*!32312 IF NOT EXISTS*/`ecommerce_db` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */;

USE `ecommerce_db`;

/*Table structure for table `order_items` */

DROP TABLE IF EXISTS `order_items`;

CREATE TABLE `order_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `order_id` int(11) NOT NULL,
  `product_id` int(11) NOT NULL,
  `quantity` int(11) NOT NULL,
  `price` float NOT NULL,
  `subtotal` float NOT NULL,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `order_items_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  CONSTRAINT `order_items_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `order_items` */

insert  into `order_items`(`id`,`order_id`,`product_id`,`quantity`,`price`,`subtotal`) values (1,1,2,2,29.99,59.98);

/*Table structure for table `orders` */

DROP TABLE IF EXISTS `orders`;

CREATE TABLE `orders` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `order_number` varchar(50) NOT NULL,
  `buyer_id` int(11) NOT NULL,
  `rider_id` int(11) DEFAULT NULL,
  `total_amount` float NOT NULL,
  `status` varchar(20) DEFAULT NULL,
  `delivery_address` text DEFAULT NULL,
  `delivery_city` varchar(80) DEFAULT NULL,
  `delivery_zip` varchar(10) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `delivered_at` datetime DEFAULT NULL,
  `seller_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_orders_order_number` (`order_number`),
  KEY `rider_id` (`rider_id`),
  KEY `ix_orders_buyer_id` (`buyer_id`),
  KEY `ix_orders_seller_id` (`seller_id`),
  CONSTRAINT `fk_orders_seller_id` FOREIGN KEY (`seller_id`) REFERENCES `users` (`id`),
  CONSTRAINT `orders_ibfk_1` FOREIGN KEY (`buyer_id`) REFERENCES `users` (`id`),
  CONSTRAINT `orders_ibfk_2` FOREIGN KEY (`rider_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `orders` */

insert  into `orders`(`id`,`order_number`,`buyer_id`,`rider_id`,`total_amount`,`status`,`delivery_address`,`delivery_city`,`delivery_zip`,`created_at`,`updated_at`,`delivered_at`,`seller_id`) values (1,'ORD-996CEB2D',3,4,59.98,'delivered','Arrieta Street','Calo','4033','2026-04-16 13:37:22','2026-04-16 13:38:15','2026-04-16 13:38:15',2);

/*Table structure for table `payments` */

DROP TABLE IF EXISTS `payments`;

CREATE TABLE `payments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `order_id` int(11) NOT NULL,
  `amount` float NOT NULL,
  `method` varchar(50) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `transaction_id` varchar(100) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_id` (`order_id`),
  UNIQUE KEY `transaction_id` (`transaction_id`),
  CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `payments` */

insert  into `payments`(`id`,`order_id`,`amount`,`method`,`status`,`transaction_id`,`created_at`,`updated_at`) values (1,1,59.98,'cod','collected',NULL,'2026-04-16 13:37:22','2026-04-16 13:38:15');

/*Table structure for table `product_images` */

DROP TABLE IF EXISTS `product_images`;

CREATE TABLE `product_images` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `product_id` int(11) NOT NULL,
  `image_url` varchar(255) NOT NULL,
  `is_primary` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `product_images_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `product_images` */

/*Table structure for table `products` */

DROP TABLE IF EXISTS `products`;

CREATE TABLE `products` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `seller_id` int(11) NOT NULL,
  `name` varchar(200) NOT NULL,
  `description` text DEFAULT NULL,
  `price` float NOT NULL,
  `stock` int(11) DEFAULT NULL,
  `category` varchar(100) DEFAULT NULL,
  `rating` float DEFAULT NULL,
  `review_count` int(11) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_products_name` (`name`),
  KEY `ix_products_seller_id` (`seller_id`),
  CONSTRAINT `products_ibfk_1` FOREIGN KEY (`seller_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `products` */

insert  into `products`(`id`,`seller_id`,`name`,`description`,`price`,`stock`,`category`,`rating`,`review_count`,`is_active`,`created_at`,`updated_at`) values (1,2,'Laptop','High-performance laptop for work and gaming',999.99,5,'Electronics',0,0,1,'2026-04-16 13:14:44','2026-04-16 13:14:44'),(2,2,'Wireless Mouse','Ergonomic wireless mouse with long battery life',29.99,48,'Accessories',0,0,1,'2026-04-16 13:14:44','2026-04-16 13:37:22'),(3,2,'USB-C Cable','Fast charging USB-C cable 6ft',12.99,100,'Accessories',0,0,1,'2026-04-16 13:14:44','2026-04-16 13:14:44'),(4,2,'Mechanical Keyboard','Professional mechanical keyboard with RGB lights',149.99,20,'Accessories',0,0,1,'2026-04-16 13:14:44','2026-04-16 13:14:44'),(5,2,'Monitor 4K','27-inch 4K UHD monitor',449.99,10,'Electronics',0,0,1,'2026-04-16 13:14:44','2026-04-16 13:14:44');

/*Table structure for table `reviews` */

DROP TABLE IF EXISTS `reviews`;

CREATE TABLE `reviews` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `product_id` int(11) NOT NULL,
  `reviewer_id` int(11) NOT NULL,
  `rating` int(11) NOT NULL,
  `comment` text DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `product_id` (`product_id`),
  KEY `reviewer_id` (`reviewer_id`),
  CONSTRAINT `reviews_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`),
  CONSTRAINT `reviews_ibfk_2` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `reviews` */

/*Table structure for table `users` */

DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(80) NOT NULL,
  `email` varchar(120) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `first_name` varchar(80) DEFAULT NULL,
  `last_name` varchar(80) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `role` varchar(20) NOT NULL,
  `shop_name` varchar(120) DEFAULT NULL,
  `shop_description` text DEFAULT NULL,
  `shop_rating` float DEFAULT NULL,
  `vehicle_type` varchar(50) DEFAULT NULL,
  `vehicle_number` varchar(50) DEFAULT NULL,
  `profile_picture` varchar(255) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `city` varchar(80) DEFAULT NULL,
  `zip_code` varchar(10) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_verified` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `valid_id` varchar(255) DEFAULT NULL,
  `business_permit` varchar(255) DEFAULT NULL,
  `drivers_license` varchar(255) DEFAULT NULL,
  `plate_number` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  UNIQUE KEY `ix_users_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `users` */

insert  into `users`(`id`,`username`,`email`,`password_hash`,`first_name`,`last_name`,`phone`,`role`,`shop_name`,`shop_description`,`shop_rating`,`vehicle_type`,`vehicle_number`,`profile_picture`,`address`,`city`,`zip_code`,`is_active`,`is_verified`,`created_at`,`updated_at`,`valid_id`,`business_permit`,`drivers_license`,`plate_number`) values (1,'admin','admin@ecommerce.com','pbkdf2:sha256:600000$72jSurfzb8waOUf5$5561e651e92538760237e89062935f4c718e8f859765b6c559c68cd2b5edd30e','Admin','User',NULL,'admin',NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,1,1,'2026-04-16 13:14:44','2026-04-16 13:14:44',NULL,NULL,NULL,NULL),(2,'seller1','seller1@ecommerce.com','pbkdf2:sha256:600000$g3cGAp7bBQuOesaA$4f743c4bd05f6d04fd4b60b04092297c5076e08e6cb382c4425293460d8f014e','John','Seller',NULL,'seller','John\'s Shop','Amazing products at great prices!',0,NULL,NULL,NULL,NULL,NULL,NULL,1,1,'2026-04-16 13:14:44','2026-04-16 13:14:44',NULL,NULL,NULL,NULL),(3,'buyer1','buyer1@ecommerce.com','pbkdf2:sha256:600000$pww7j8NgaWPGJ6bW$e82de05d823e585858de8c2a92edd85256048c292a80cbf858c8d78853427c59','Jane','Buyer',NULL,'buyer',NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,1,1,'2026-04-16 13:14:44','2026-04-16 13:14:44',NULL,NULL,NULL,NULL),(4,'rider1','rider1@ecommerce.com','pbkdf2:sha256:600000$g2Hf4NPyuURCmiL2$80557b39f4e2f54fe5a109c9294a2765dac1086ffc3e08104980cc4a462052a5','Mike','Rider',NULL,'rider',NULL,NULL,0,'Bike','AB-1234',NULL,NULL,NULL,NULL,1,1,'2026-04-16 13:14:44','2026-04-16 13:14:44',NULL,NULL,NULL,NULL);

/*Table structure for table `wishlists` */

DROP TABLE IF EXISTS `wishlists`;

CREATE TABLE `wishlists` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `product_id` int(11) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_wishlist_user_product` (`user_id`,`product_id`),
  KEY `product_id` (`product_id`),
  KEY `ix_wishlists_user_id` (`user_id`),
  CONSTRAINT `wishlists_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `wishlists_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `wishlists` */

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

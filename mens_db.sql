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

/*Table structure for table `cart_items` */

DROP TABLE IF EXISTS `cart_items`;

CREATE TABLE `cart_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `product_id` int(11) NOT NULL,
  `variant_id` int(11) DEFAULT NULL,
  `quantity` int(11) NOT NULL,
  `added_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_cart_user_product_variant` (`user_id`,`product_id`,`variant_id`),
  KEY `product_id` (`product_id`),
  KEY `variant_id` (`variant_id`),
  KEY `ix_cart_items_user_id` (`user_id`),
  CONSTRAINT `cart_items_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `cart_items_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`),
  CONSTRAINT `cart_items_ibfk_3` FOREIGN KEY (`variant_id`) REFERENCES `product_variants` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `cart_items` */

/*Table structure for table `messages` */

DROP TABLE IF EXISTS `messages`;

CREATE TABLE `messages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `sender_id` int(11) NOT NULL,
  `receiver_id` int(11) NOT NULL,
  `product_id` int(11) DEFAULT NULL,
  `order_id` int(11) DEFAULT NULL,
  `body` text NOT NULL,
  `is_read` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `product_id` (`product_id`),
  KEY `order_id` (`order_id`),
  KEY `ix_messages_receiver_id` (`receiver_id`),
  KEY `ix_messages_sender_id` (`sender_id`),
  KEY `ix_messages_created_at` (`created_at`),
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`),
  CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`id`),
  CONSTRAINT `messages_ibfk_3` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`),
  CONSTRAINT `messages_ibfk_4` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `messages` */

insert  into `messages`(`id`,`sender_id`,`receiver_id`,`product_id`,`order_id`,`body`,`is_read`,`created_at`) values (1,3,2,2,NULL,'hello',1,'2026-04-16 19:34:51'),(2,2,3,NULL,NULL,'hi',1,'2026-04-16 19:35:08');

/*Table structure for table `order_items` */

DROP TABLE IF EXISTS `order_items`;

CREATE TABLE `order_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `order_id` int(11) NOT NULL,
  `product_id` int(11) NOT NULL,
  `quantity` int(11) NOT NULL,
  `price` float NOT NULL,
  `subtotal` float NOT NULL,
  `variant_id` int(11) DEFAULT NULL,
  `variant_size` varchar(30) DEFAULT NULL,
  `variant_color` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `order_items_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  CONSTRAINT `order_items_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `order_items` */

insert  into `order_items`(`id`,`order_id`,`product_id`,`quantity`,`price`,`subtotal`,`variant_id`,`variant_size`,`variant_color`) values (1,1,2,2,29.99,59.98,NULL,NULL,NULL),(2,2,2,1,129.99,129.99,NULL,NULL,NULL),(3,3,7,1,1500,1500,6,'XXL','Olive Green'),(4,4,7,1,1500,1500,3,'M','Olive Green');

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
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `orders` */

insert  into `orders`(`id`,`order_number`,`buyer_id`,`rider_id`,`total_amount`,`status`,`delivery_address`,`delivery_city`,`delivery_zip`,`created_at`,`updated_at`,`delivered_at`,`seller_id`) values (1,'ORD-996CEB2D',3,4,59.98,'delivered','Arrieta Street','Calo','4033','2026-04-16 13:37:22','2026-04-16 13:38:15','2026-04-16 13:38:15',2),(2,'ORD-E69AB114',3,4,129.99,'delivered','Bagumbayan, Santa Cruz, Laguna, CALABARZON','Santa Cruz','','2026-04-16 18:22:40','2026-04-16 18:26:51','2026-04-16 18:26:51',2),(3,'ORD-C40598B7',3,4,1500,'delivered','Bagumbayan, Santa Cruz, Laguna, CALABARZON','Santa Cruz','','2026-04-16 19:13:10','2026-04-16 19:17:46','2026-04-16 19:17:46',2),(4,'ORD-D62D9148',6,4,1500,'delivered','586. F Arrieta Street, Calo, Bay, Laguna, CALABARZON','Bay','4033','2026-04-16 20:04:35','2026-04-16 20:06:50','2026-04-16 20:06:50',2);

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
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `payments` */

insert  into `payments`(`id`,`order_id`,`amount`,`method`,`status`,`transaction_id`,`created_at`,`updated_at`) values (1,1,59.98,'cod','collected',NULL,'2026-04-16 13:37:22','2026-04-16 13:38:15'),(2,2,129.99,'cod','collected',NULL,'2026-04-16 18:22:40','2026-04-16 18:26:51'),(3,3,1500,'cod','collected',NULL,'2026-04-16 19:13:10','2026-04-16 19:17:46'),(4,4,1500,'cod','collected',NULL,'2026-04-16 20:04:35','2026-04-16 20:06:50');

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
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `product_images` */

insert  into `product_images`(`id`,`product_id`,`image_url`,`is_primary`,`created_at`) values (1,2,'8a8836f9f89d43e8b6107a37d7621599.png',1,'2026-04-16 15:56:20'),(2,6,'b1ef3d3a2edd479987e275cf186e55eb.png',1,'2026-04-16 15:58:21'),(3,7,'ee4b719869ef41f39f0a956602023d4e.png',1,'2026-04-16 19:00:04'),(4,8,'613ed3c7e859432e91d4b3e5adbe02eb.png',1,'2026-04-17 03:53:20'),(5,8,'39fce518c2394358806a3ae916b5fe69.png',0,'2026-04-17 03:53:39');

/*Table structure for table `product_variants` */

DROP TABLE IF EXISTS `product_variants`;

CREATE TABLE `product_variants` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `product_id` int(11) NOT NULL,
  `size` varchar(30) NOT NULL,
  `color` varchar(50) DEFAULT NULL,
  `sku` varchar(100) DEFAULT NULL,
  `stock` int(11) NOT NULL,
  `price_adj` float DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_product_variants_product_id` (`product_id`),
  KEY `ix_product_variants_sku` (`sku`),
  CONSTRAINT `product_variants_ibfk_1` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `product_variants` */

insert  into `product_variants`(`id`,`product_id`,`size`,`color`,`sku`,`stock`,`price_adj`,`created_at`) values (1,7,'XS','Olive Green','7-XS-Olive Green',3,0,'2026-04-16 19:00:04'),(2,7,'S','Olive Green','7-S-Olive Green',4,0,'2026-04-16 19:00:04'),(3,7,'M','Olive Green','7-M-Olive Green',5,0,'2026-04-16 19:00:04'),(4,7,'L','Olive Green','7-L-Olive Green',7,0,'2026-04-16 19:00:04'),(5,7,'XL','Olive Green','7-XL-Olive Green',8,0,'2026-04-16 19:00:04'),(6,7,'XXL','Olive Green','7-XXL-Olive Green',2,0,'2026-04-16 19:00:04'),(7,8,'38','Red','8-38-Red',5,0,'2026-04-17 03:53:20'),(8,8,'39','Red','8-39-Red',10,0,'2026-04-17 03:53:20'),(9,8,'40','Red','8-40-Red',7,0,'2026-04-17 03:53:20'),(10,8,'41','Red','8-41-Red',15,0,'2026-04-17 03:53:20'),(11,8,'42','Red','8-42-Red',22,0,'2026-04-17 03:53:20'),(12,8,'43','Red','8-43-Red',8,0,'2026-04-17 03:53:20'),(13,8,'44','Red','8-44-Red',1,0,'2026-04-17 03:53:20'),(14,8,'45','Red','8-45-Red',0,0,'2026-04-17 03:53:20');

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
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `products` */

insert  into `products`(`id`,`seller_id`,`name`,`description`,`price`,`stock`,`category`,`rating`,`review_count`,`is_active`,`created_at`,`updated_at`) values (2,2,'Shaver','wireless shaver with long lasting battery life.',129.99,14,'Grooming Products',0,0,1,'2026-04-16 13:14:44','2026-04-16 18:22:40'),(6,2,'Shaving Foam','',200,10,'Grooming Products',0,0,1,'2026-04-16 15:58:21','2026-04-16 15:58:21'),(7,2,'Olive Green Suit','',1500,29,'Suits & Blazers',2,1,1,'2026-04-16 19:00:04','2026-04-17 04:11:29'),(8,2,'Puma Speedcat','The PUMA Speedcat has been an icon of racing culture and street style for decades. The world first knew it as an ultra-slim driving shoe.',7100,68,'Shoes & Accessories',0,0,1,'2026-04-17 03:53:20','2026-04-17 03:53:20');

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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `reviews` */

insert  into `reviews`(`id`,`product_id`,`reviewer_id`,`rating`,`comment`,`created_at`,`updated_at`) values (1,7,3,2,'The quality is excellent.','2026-04-17 04:11:29','2026-04-17 04:11:29');

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
  `email_verified` tinyint(1) NOT NULL DEFAULT 0,
  `email_verify_token` varchar(100) DEFAULT NULL,
  `reset_token` varchar(100) DEFAULT NULL,
  `reset_token_expiry` datetime DEFAULT NULL,
  `region` varchar(120) DEFAULT NULL,
  `province` varchar(120) DEFAULT NULL,
  `municipality` varchar(120) DEFAULT NULL,
  `barangay` varchar(120) DEFAULT NULL,
  `street` varchar(255) DEFAULT NULL,
  `is_banned` tinyint(1) NOT NULL DEFAULT 0,
  `ban_reason` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  UNIQUE KEY `ix_users_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `users` */

insert  into `users`(`id`,`username`,`email`,`password_hash`,`first_name`,`last_name`,`phone`,`role`,`shop_name`,`shop_description`,`shop_rating`,`vehicle_type`,`vehicle_number`,`profile_picture`,`address`,`city`,`zip_code`,`is_active`,`is_verified`,`created_at`,`updated_at`,`valid_id`,`business_permit`,`drivers_license`,`plate_number`,`email_verified`,`email_verify_token`,`reset_token`,`reset_token_expiry`,`region`,`province`,`municipality`,`barangay`,`street`,`is_banned`,`ban_reason`) values (1,'admin','admin@ecommerce.com','pbkdf2:sha256:600000$72jSurfzb8waOUf5$5561e651e92538760237e89062935f4c718e8f859765b6c559c68cd2b5edd30e','Admin','User',NULL,'admin',NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,1,1,'2026-04-16 13:14:44','2026-04-16 13:14:44',NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL),(2,'seller1','seller1@ecommerce.com','pbkdf2:sha256:600000$g3cGAp7bBQuOesaA$4f743c4bd05f6d04fd4b60b04092297c5076e08e6cb382c4425293460d8f014e','John','Seller',NULL,'seller','John\'s Shop','Amazing products at great prices!',0,NULL,NULL,NULL,NULL,NULL,NULL,1,1,'2026-04-16 13:14:44','2026-04-16 13:14:44',NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL),(3,'buyer1','buyer1@ecommerce.com','pbkdf2:sha256:600000$pww7j8NgaWPGJ6bW$e82de05d823e585858de8c2a92edd85256048c292a80cbf858c8d78853427c59','Jane','Buyer','','buyer',NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,'',1,1,'2026-04-16 13:14:44','2026-04-16 17:06:56',NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,'CALABARZON','Laguna','Santa Cruz','Bagumbayan','',0,NULL),(4,'rider1','rider1@ecommerce.com','pbkdf2:sha256:600000$g2Hf4NPyuURCmiL2$80557b39f4e2f54fe5a109c9294a2765dac1086ffc3e08104980cc4a462052a5','Mike','Rider',NULL,'rider',NULL,NULL,0,'Bike','AB-1234',NULL,NULL,NULL,NULL,1,1,'2026-04-16 13:14:44','2026-04-16 13:14:44',NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL),(6,'chardi','veluz.richard@gmail.com','pbkdf2:sha256:600000$DiCgrKz82ZLsOKuR$82ded04a27baa5acdfe70f3a616ef8f6683e3a04b2de1870b314b92417815a5c','Richard','Veluz','09694783874','buyer',NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,'4033',1,1,'2026-04-16 15:29:47','2026-04-16 15:46:15','docs/6e8fa859c15142fa8146106d27df843d.jpg',NULL,NULL,NULL,1,NULL,'04570c75ac9140c3996c832124843207','2026-04-16 16:30:49','CALABARZON','Laguna','Bay','Calo','586. F Arrieta Street',0,NULL);

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
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

/*Data for the table `wishlists` */

insert  into `wishlists`(`id`,`user_id`,`product_id`,`created_at`) values (2,6,7,'2026-04-16 20:04:17'),(3,3,8,'2026-04-17 03:56:40');

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

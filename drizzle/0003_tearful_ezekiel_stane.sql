CREATE TABLE `field_observations` (
	`id` int AUTO_INCREMENT NOT NULL,
	`reporter_user_id` int NOT NULL,
	`observed_at` timestamp NOT NULL,
	`latitude` decimal(9,6) NOT NULL,
	`longitude` decimal(9,6) NOT NULL,
	`location_accuracy_m` decimal(9,1),
	`impact_class` enum('flooded','water_on_road','access_disrupted','no_flood_observed') NOT NULL,
	`water_depth_cm` decimal(8,1),
	`notes` text,
	`photo_key` varchar(255),
	`photo_content_type` varchar(120),
	`review_status` enum('submitted','verified','rejected') NOT NULL DEFAULT 'submitted',
	`review_notes` text,
	`reviewer_user_id` int,
	`reviewed_at` timestamp,
	`created_at` timestamp NOT NULL DEFAULT (now()),
	`updated_at` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `field_observations_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE INDEX `field_observations_review_observed` ON `field_observations` (`review_status`,`observed_at`);--> statement-breakpoint
CREATE INDEX `field_observations_reporter` ON `field_observations` (`reporter_user_id`);
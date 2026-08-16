CREATE TABLE `rainfall_history` (
	`id` int AUTO_INCREMENT NOT NULL,
	`source_key` varchar(120) NOT NULL,
	`observed_date` varchar(10) NOT NULL,
	`precipitation_mm` decimal(8,2) NOT NULL,
	`accumulation_7d_mm` decimal(9,2) NOT NULL,
	`created_at` timestamp NOT NULL DEFAULT (now()),
	`updated_at` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `rainfall_history_id` PRIMARY KEY(`id`),
	CONSTRAINT `rainfall_history_source_date` UNIQUE(`source_key`,`observed_date`)
);
--> statement-breakpoint
CREATE TABLE `schedule_configs` (
	`id` int AUTO_INCREMENT NOT NULL,
	`key` varchar(80) NOT NULL,
	`schedule_cron_task_uid` varchar(65),
	`last_run_at` timestamp,
	`last_result` json,
	`created_at` timestamp NOT NULL DEFAULT (now()),
	`updated_at` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `schedule_configs_id` PRIMARY KEY(`id`),
	CONSTRAINT `schedule_configs_key_unique` UNIQUE(`key`)
);
--> statement-breakpoint
ALTER TABLE `users` MODIFY COLUMN `role` enum('admin','user') NOT NULL DEFAULT 'user';
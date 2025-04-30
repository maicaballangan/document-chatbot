INSERT INTO "user"("password",last_login,is_superuser,first_name,last_name,is_staff,is_active,created_at,modified_at,email,register_token,invite_token,stripe_customer_id) 
VALUES ('pbkdf2_sha256$600000$rWvO0CKxAcKyfzVe9iOBmD$M+reMFrptGY7oKPvOjkVsU/L2+zE+80nufv07yXjT88=','2025-01-22 01:03:51.420',true,'admin','admin',true,true,'2024-12-22 22:29:37.317','2024-12-22 22:29:37.317','admin@example.ai',null,null,null);

INSERT INTO user_subscription (created_at, modified_at, stripe_subscription_id, status, user_id, subscription_plan_id, current_period_end, trial_period_end, expired_at)
VALUES ('2025-01-21 17:55:38.08676+00','2025-01-21 17:55:38.086765+00','888d3edb-b116-4a9a-ad26-f2b40baca91a','active',1,6,null,'2030-02-20 05:00:00+00',null);
